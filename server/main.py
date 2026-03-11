from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
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
import re
import json
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

def get_safe_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

# Local imports
from .models import CheckBatch, Check, CheckStatus, Base, AuditLog, User
from .database import get_db, engine, SessionLocal
from .ai_extractor import extract_check_data_via_ai
from .validators import validate_extracted_check_data
from .export import generate_accounting_spreadsheet
from .security import get_current_user, get_password_hash, verify_password, create_access_token

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None

# ── Logging: structured stdout (works in any hosting env) ──────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("quicktrack")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Quick Track Check System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Wildcard for easier debugging, will restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health (Defined EARLY to ensure availability) ──────────────────────────────
@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/")
async def root():
    return {
        "message": "QuickTrack API is live",
        "health": "/api/health",
        "debug": "/api/debug/db",
        "status": "ready"
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f'"REQUEST: {request.method} {request.url.path}"')
    try:
        response = await call_next(request)
        logger.info(f'"RESPONSE: {response.status_code} {request.url.path}"')
        return response
    except HTTPException as http_exc:
        # Don't mask 401/404/etc as 500
        logger.warning(f'"HTTP {http_exc.status_code}: {http_exc.detail} for {request.url.path}"')
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"detail": http_exc.detail}
        )
    except Exception as e:
        logger.error(f'"CRITICAL ERROR: {str(e)} for {request.url.path}"')
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )

# ── APP STARTUP MARKER ────────────────────────────────────────────────────────
logger.info('"--- QUICKTRACK BACKEND INITIALIZING ---"')

@app.on_event("startup")
async def startup_event():
    logger.info('"Booting startup event loop..."')
    async def init_db_async():
        try:
            logger.info('"Starting background database initialization..."')
            # Run the blocking create_all in a threadpool
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: Base.metadata.create_all(bind=engine))
            logger.info('"Database tables initialized/verified in background"')

            with SessionLocal() as db:
                if db.query(User).count() == 0:
                    pw_hash = get_password_hash("Quicktrackinc@2026!")
                    admin_user = User(username="admin", password_hash=pw_hash, role="ADMIN")
                    db.add(admin_user)
                    db.commit()
                    logger.info('"Default admin user created."')
        except Exception as e:
            logger.error(f'"Background database initialization failed: {str(e)}"')

    # FIRE AND FORGET - do NOT await this. 
    # This allows the healthcheck to respond even if the DB is slow/cold starting.
    import asyncio
    asyncio.create_task(init_db_async())

# ── Static Files ──────────────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
# Use absolute paths where possible
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fallback logic for Railway Volumes
UPLOAD_ROOT = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "public")
UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "uploads")

try:
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f'"Upload directory verified at: {UPLOAD_DIR}"')
except Exception as e:
    logger.error(f'"Volume mount failed, falling back to local: {str(e)}"')
    UPLOAD_DIR = os.path.join(BASE_DIR, "public", "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/api/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/api/public/debug-db")
async def public_debug_db(db: Session = Depends(get_db)):
    """Public version of debug check (no auth required)"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "Database Connection OK"}
    except Exception as e:
        return {"status": "Database Connection Failed", "error": str(e)}

@app.get("/api/debug/db")
async def debug_db(db: Session = Depends(get_db)):
    """Check if we can connect to the DB and see the tables."""
    try:
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check if we can query
        count = db.query(CheckBatch).count()
        
        return {
            "status": "connected",
            "tables": tables,
            "batch_count": count,
            "db_url_type": engine.url.drivername
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc().split("\n")[-5:]
        }

@app.get("/api/debug/s3")
async def debug_s3():
    """Check if S3 environment variables are loaded."""
    return {
        "AWS_ACCESS_KEY_ID": "Found" if os.getenv("AWS_ACCESS_KEY_ID") else "Missing",
        "AWS_REGION": os.getenv("AWS_REGION"),
        "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME"),
        "ENV_FILE_PATH": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"),
        "ENV_FILE_EXISTS": os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))
    }

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

    safe_name = get_safe_filename(file.filename)
    object_name = f"{batch_id}_{safe_name}"

    # S3 Upload Setup
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

    logger.info(f'"Checking S3 credentials: ID={"Found" if AWS_ACCESS_KEY_ID else "Missing"} Bucket={"Found" if S3_BUCKET_NAME else "Missing"}"')

    if AWS_ACCESS_KEY_ID and S3_BUCKET_NAME:
        import boto3
        from botocore.exceptions import ClientError
        
        logger.info(f'"Attempting S3 upload to {S3_BUCKET_NAME} in {AWS_REGION}..."')
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )
            
            # Upload the file bytes to S3
            s3_client.upload_fileobj(
                io.BytesIO(file_bytes),
                S3_BUCKET_NAME,
                object_name,
                ExtraArgs={'ContentType': file.content_type}
            )
            logger.info(f'"Successfully uploaded {object_name} to S3 bucket {S3_BUCKET_NAME}"')

            # Generate a pre-signed URL (valid for 7 days - maximum allowed by AWS)
            # The frontend will use this URL to display the image securely
            s3_mock_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': object_name},
                ExpiresIn=604800 # 7 days
            )
        except Exception as e:
            logger.error(f'"Failed to upload to S3 or generate URL: {str(e)}"')
            # Fallback to local if S3 fails
            file_path = os.path.join(UPLOAD_DIR, object_name)
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)
            s3_mock_url = f"/api/uploads/{object_name}"
    else:
        # Save locally if S3 is not configured
        file_path = os.path.join(UPLOAD_DIR, object_name)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        s3_mock_url = f"/api/uploads/{object_name}"

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
                "created_at": getattr(batch, "created_at", datetime.utcnow()).replace(tzinfo=timezone.utc).isoformat(),
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
    if user.get("role") != "ADMIN":
        logger.warning(f'"Unauthorized delete attempt by {user.get("username")} on batch {batch_id}"')
        raise HTTPException(status_code=403, detail="Only Admins can delete batches")

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

    old_values = {
        "status": check.status.value,
        "store_name": check.store_name,
        "check_number": check.check_number,
        "check_date": check.check_date.isoformat() if check.check_date else None,
        "payee": check.payee,
        "amount": check.amount,
        "memo": check.memo,
        "bank_name": check.bank,
        "routing_number": check.routing_number,
        "account_number": check.account_number,
    }

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

    new_values = {
        "status": check.status.value,
        "store_name": check.store_name,
        "check_number": check.check_number,
        "check_date": check.check_date.isoformat() if check.check_date else None,
        "payee": check.payee,
        "amount": check.amount,
        "memo": check.memo,
        "bank_name": check.bank,
        "routing_number": check.routing_number,
        "account_number": check.account_number,
    }

    changes = {}
    for k, v in new_values.items():
        if old_values[k] != v:
            changes[k] = {"old": old_values[k], "new": v}

    if changes:
        action = "APPROVED" if changes.get("status", {}).get("new") == "APPROVED" else "UPDATED"
        audit = AuditLog(
            check_id=check.id,
            user=user["username"],
            action=action,
            changes=json.dumps(changes)
        )
        db.add(audit)

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

@app.get("/api/checks/{check_id}/audit")
async def get_check_audit(check_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch history of changes for a specific check."""
    logs = db.query(AuditLog).filter(AuditLog.check_id == check_id).order_by(AuditLog.created_at.desc()).all()
    return {
        "check_id": check_id,
        "history": [
            {
                "id": log.id,
                "user": log.user,
                "action": log.action,
                "changes": json.loads(log.changes) if log.changes else {},
                "created_at": log.created_at.replace(tzinfo=timezone.utc).isoformat()
            } for log in logs
        ]
    }

@app.get("/api/audit")
async def get_global_audit(skip: int = 0, limit: int = 50, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch global history of all changes across the system (Admins only)."""
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can view the global audit log")

    # Join with Check and CheckBatch to get more context
    logs = db.query(AuditLog, Check).join(Check).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.AuditLog.id,
                "check_id": log.AuditLog.check_id,
                "batch_id": log.Check.batch_id,
                "user": log.AuditLog.user,
                "action": log.AuditLog.action,
                "changes": json.loads(log.AuditLog.changes) if log.AuditLog.changes else {},
                "created_at": log.AuditLog.created_at.replace(tzinfo=timezone.utc).isoformat()
            } for log in logs
        ]
    }

# ── Export ─────────────────────────────────────────────────────────────────────
@app.get("/api/checks/export")
def download_batch_spreadsheet(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export approved checks in batch to Excel format."""
    if not db.query(CheckBatch).filter(CheckBatch.id == batch_id).first():
        raise HTTPException(status_code=404, detail="Batch ID not found")

    batch_number = db.query(CheckBatch).filter(CheckBatch.id <= batch_id).count()
    excel_stream = generate_accounting_spreadsheet(db, batch_id)
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=QuickTrack_Batch_{batch_number}_Export.xlsx"}
    )

@app.get("/api/checks/export/csv")
def download_batch_csv(batch_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export approved checks in batch to CSV format."""
    checks = db.query(Check).filter(Check.batch_id == batch_id).all()
    if not checks:
        raise HTTPException(status_code=404, detail="No checks found for this batch")

    batch_number = db.query(CheckBatch).filter(CheckBatch.id <= batch_id).count()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Batch Number", "Date", "Store", "Payee", "Amount",
        "Bank Name", "Routing Number", "Account Number", "Check Number", "Memo", "Status", "Reviewed By"
    ])

    for check in checks:
        # Format the amount to accounting standard
        formatted_amount = f"${check.amount:,.2f}" if check.amount is not None else "$0.00"
        
        # Format date cleanly
        formatted_date = check.check_date.strftime("%Y-%m-%d") if check.check_date else "N/A"

        writer.writerow([
            batch_number, 
            formatted_date,
            check.store_name or "N/A", 
            check.payee or "N/A", 
            formatted_amount,
            check.bank or "N/A", 
            check.routing_number or "N/A",
            check.account_number or "N/A",
            check.check_number or "N/A", 
            check.memo or "N/A", 
            check.status.value, 
            check.reviewed_by or "Auto"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=QuickTrack_Batch_{batch_number}_Export.csv"}
    )

# ── User Management & Auth ────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Verifies user credentials and returns a JWT."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "role": user.role}

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Fetch all users (Admins only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can view users.")
    users = db.query(User).all()
    return {"users": [{"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at.replace(tzinfo=timezone.utc).isoformat() if u.created_at else None} for u in users]}

@app.post("/api/users")
async def create_user(req: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create a new user (Admins only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can create users.")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        role=req.role.upper()
    )
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Update a user's role or password (Admins only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can edit users.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent the last Admin from being downgraded
    if req.role and req.role.upper() != "ADMIN" and user.role == "ADMIN":
        admin_count = db.query(User).filter(User.role == "ADMIN").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot downgrade the last Admin.")
    
    if req.password:
        user.password_hash = get_password_hash(req.password)
    if req.role:
        user.role = req.role.upper()
        
    db.commit()
    return {"message": "User updated successfully"}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Delete a user (Admins only)."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only Admins can delete users.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot delete yourself.")
        
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

