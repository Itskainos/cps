from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone, date
from pydantic import BaseModel
from typing import Optional
import io
import csv
import logging
import traceback
import os

# Local imports
from .models import CheckBatch, Check, CheckStatus, Base
from .database import get_db, engine
from .ai_extractor import extract_check_data_via_ai
from .validators import validate_extracted_check_data
from .export import generate_accounting_spreadsheet
from .security import get_current_user

# ── Logging: structured stdout (works in any hosting env) ──────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("quicktrack")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Quick Track Check System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://cps-mu.vercel.app",   # production Vercel URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f'"Incoming {request.method} {request.url.path}"')
    try:
        response = await call_next(request)
        logger.info(f'"Response {response.status_code} {request.url.path}"')
        return response
    except Exception as e:
        logger.error(f'"Middleware error: {str(e)}"')
        logger.error(traceback.format_exc())
        raise e

# ── Database Initialization ─────────────────────────────────────────────────────
# Create tables if they don't exist (Runs on every startup)
try:
    Base.metadata.create_all(bind=engine)
    logger.info('"Database tables initialized/verified"')
except Exception as e:
    logger.error(f'"Database connection failed: {str(e)}"')

from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = os.path.join(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "public"), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ── Stats ──────────────────────────────────────────────────────────────────────
@app.get("/api/checks/stats")
async def get_stats(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Summary counts for the dashboard stats cards."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    total_batches    = db.query(CheckBatch).count()
    pending_count    = db.query(Check).filter(Check.status == CheckStatus.PENDING).count()
    review_count     = db.query(Check).filter(Check.status == CheckStatus.MANUAL_REVIEW).count()
    approved_today   = db.query(Check).filter(
        Check.status == CheckStatus.APPROVED,
        Check.reviewed_at >= today_start
    ).count()

    return {
        "total_batches":   total_batches,
        "pending_checks":  pending_count,
        "review_checks":   review_count,
        "approved_today":  approved_today,
    }

# ── Request Models ─────────────────────────────────────────────────────────────
class CheckApprovalUpdate(BaseModel):
    status: str
    store_name: Optional[str] = None
    check_number: Optional[str] = None
    check_date: Optional[str] = None
    payee: Optional[str] = None
    amount: Optional[float] = None
    memo: Optional[str] = None
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None

# ── Upload / Extract ───────────────────────────────────────────────────────────
@app.post("/api/checks/upload")
async def create_upload_batch(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Creates a new CheckBatch wrapper to tie subsequent uploads to."""
    new_batch = CheckBatch(
        created_by=user["username"],
        status=CheckStatus.PENDING
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    logger.info(f'"Batch created: id={new_batch.id} by={user["username"]}"')
    return {"batch_id": new_batch.id, "status": new_batch.status}

@app.post("/api/checks/extract")
async def extract_check_image(
    batch_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads single check, performs OCR, and attaches to Batch ID."""
    batch = db.query(CheckBatch).filter(CheckBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch ID not found")

    file_bytes = await file.read()

    # AI Extraction
    try:
        extracted_data = await extract_check_data_via_ai(file_bytes, file.filename)
    except Exception as e:
        logger.error(f'"AI extraction failed for {file.filename}: {str(e)}"')
        raise HTTPException(status_code=500, detail=f"AI parsing failed: {e}")

    # Validation
    status_str, notes = validate_extracted_check_data(extracted_data)

    # Save locally (or to attached volume on Railway)
    # This ensures uploads aren't lost when the Railway container restarts
    file_path = os.path.join(UPLOAD_DIR, f"{batch_id}_{safe_filename}")
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Since the frontend doesn't host these files anymore in production, 
    # we point them to the backend's new static file route
    s3_mock_url = f"/api/uploads/{batch_id}_{safe_filename}"

    # Date parse
    date_obj = None
    try:
        if extracted_data.get("check_date"):
            date_obj = datetime.strptime(extracted_data.get("check_date"), "%Y-%m-%d").date()
    except ValueError:
        pass

    new_check = Check(
        batch_id=batch_id,
        store_name=extracted_data.get("store_name"),
        check_number=extracted_data.get("check_number"),
        check_date=date_obj,
        payee=extracted_data.get("payee_name"),
        amount=extracted_data.get("amount"),
        memo=extracted_data.get("memo"),
        bank=extracted_data.get("bank_name"),
        routing_number=extracted_data.get("routing_number"),
        account_number=extracted_data.get("account_number"),
        confidence_score=extracted_data.get("confidence_score"),
        status=CheckStatus(status_str),
        validation_notes=notes,
        s3_image_url=s3_mock_url
    )

    db.add(new_check)
    db.commit()
    db.refresh(new_check)

    logger.info(f'"Check extracted: id={new_check.id} batch={batch_id} status={status_str}"')
    return {
        "check_id": new_check.id,
        "status": new_check.status,
        "confidence_score": new_check.confidence_score,
        "notes": new_check.validation_notes
    }

# ── Batches ────────────────────────────────────────────────────────────────────
@app.get("/api/checks/batches")
async def get_all_batches(
    skip: int = 0,
    limit: int = 20,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve batches for the Dashboard with pagination support."""
    try:
        # All batches ascending to compute sequential numbers, then paginate
        all_batches = db.query(CheckBatch).order_by(CheckBatch.id.asc()).all()
        total = len(all_batches)

        dashboard_data = []
        for display_number, batch in enumerate(all_batches, start=1):
            total_checks = db.query(Check).filter(Check.batch_id == batch.id).count()
            processed_checks = db.query(Check).filter(
                Check.batch_id == batch.id,
                Check.status.in_([CheckStatus.APPROVED, CheckStatus.REJECTED])
            ).count()

            dashboard_data.append({
                "batch_id": batch.id,
                "batch_number": display_number,
                "status": "APPROVED" if (total_checks > 0 and processed_checks == total_checks) else batch.status.value,
                "created_by": batch.created_by,
                "created_at": getattr(batch, "created_at", datetime.utcnow()).isoformat(),
                "total_checks": total_checks,
                "approved_checks": processed_checks,
            })

        # Newest first, then paginate
        dashboard_data.reverse()
        paginated = dashboard_data[skip: skip + limit]

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "batches": paginated,
        }

    except Exception as e:
        logger.error(f'"GET /api/checks/batches error: {str(e)}"')
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/checks/batch/{batch_id}")
async def get_batch_details(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve full batch data for UI review."""
    batch = db.query(CheckBatch).filter(CheckBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch ID not found")

    checks = db.query(Check).filter(Check.batch_id == batch_id).all()
    batch_number = db.query(CheckBatch).filter(CheckBatch.id <= batch_id).count()

    return {
        "batch_id": batch.id,
        "batch_number": batch_number,
        "status": batch.status,
        "created_by": batch.created_by,
        "checks": [
            {
                "id": c.id,
                "store_name": c.store_name,
                "check_number": c.check_number,
                "check_date": c.check_date.isoformat() if hasattr(c.check_date, 'isoformat') else c.check_date,
                "payee": c.payee,
                "amount": c.amount,
                "memo": c.memo,
                "bank_name": c.bank,
                "routing_number": c.routing_number,
                "account_number": c.account_number,
                "status": c.status,
                "confidence_score": c.confidence_score,
                "validation_notes": c.validation_notes,
                "s3_image_url": c.s3_image_url
            } for c in checks
        ]
    }

@app.delete("/api/checks/batch/{batch_id}")
async def delete_batch(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a batch and all its associated checks."""
    batch = db.query(CheckBatch).filter(CheckBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    db.query(Check).filter(Check.batch_id == batch_id).delete()
    db.delete(batch)
    db.commit()
    logger.info(f'"Batch deleted: id={batch_id} by={user["username"]}"')
    return {"message": f"Batch {batch_id} successfully deleted"}

# ── Review ─────────────────────────────────────────────────────────────────────
@app.patch("/api/checks/{check_id}")
async def review_check(
    check_id: int,
    update_data: CheckApprovalUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handles manual review overrides and Approval."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check ID not found")

    if update_data.status not in [e.value for e in CheckStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")

    check.status = CheckStatus(update_data.status)
    check.reviewed_by = user["username"]
    check.reviewed_at = datetime.utcnow()

    if update_data.store_name is not None:    check.store_name    = update_data.store_name
    if update_data.check_number is not None:  check.check_number  = update_data.check_number
    if update_data.payee is not None:         check.payee         = update_data.payee
    if update_data.amount is not None:        check.amount        = update_data.amount
    if update_data.memo is not None:          check.memo          = update_data.memo
    if update_data.bank_name is not None:     check.bank          = update_data.bank_name
    if update_data.routing_number is not None: check.routing_number = update_data.routing_number
    if update_data.account_number is not None: check.account_number = update_data.account_number

    if update_data.check_date is not None:
        try:
            check.check_date = datetime.strptime(update_data.check_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    db.commit()
    db.refresh(check)

    # Auto-approve batch if all checks done
    total_checks    = db.query(Check).filter(Check.batch_id == check.batch_id).count()
    approved_checks = db.query(Check).filter(Check.batch_id == check.batch_id, Check.status == CheckStatus.APPROVED).count()

    if total_checks > 0 and approved_checks == total_checks:
        batch = db.query(CheckBatch).filter(CheckBatch.id == check.batch_id).first()
        if batch and batch.status != CheckStatus.APPROVED:
            batch.status = CheckStatus.APPROVED
            db.commit()

    return {"check_id": check.id, "status": check.status, "reviewed_by": check.reviewed_by}

# ── Export ─────────────────────────────────────────────────────────────────────
@app.get("/api/checks/export")
def download_batch_spreadsheet(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export approved checks in batch to Excel format."""
    if not db.query(CheckBatch).filter(CheckBatch.id == batch_id).first():
        raise HTTPException(status_code=404, detail="Batch ID not found")

    excel_stream = generate_accounting_spreadsheet(db, batch_id)
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=QuickTrack_Batch_{batch_id}_Export.xlsx"}
    )

@app.get("/api/checks/export/csv")
def download_batch_csv(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export approved checks in batch to CSV format."""
    checks = db.query(Check).filter(Check.batch_id == batch_id).all()
    if not checks:
        raise HTTPException(status_code=404, detail="No checks found for this batch")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Batch ID", "Store", "Check Number", "Date", "Payee", "Amount",
        "Memo", "Bank", "Status", "Reviewed By", "Reviewed At"
    ])

    for check in checks:
        writer.writerow([
            check.batch_id, check.store_name, check.check_number,
            check.check_date.strftime("%Y-%m-%d") if check.check_date else None,
            check.payee, check.amount, check.memo, check.bank,
            check.status.value, check.reviewed_by,
            check.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if check.reviewed_at else None
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=QuickTrack_Batch_{batch_id}_Export.csv"}
    )
