import pandas as pd
from sqlalchemy.orm import Session
from io import BytesIO
from .models import Check, CheckBatch

def generate_accounting_spreadsheet(db: Session, batch_id: int) -> BytesIO:
    """
    Generates accurately formatted PRD 3 Accounting Spreadsheet.
    """
    checks = db.query(Check).filter(Check.batch_id == batch_id).all()
    batch_number = db.query(CheckBatch).filter(CheckBatch.id <= batch_id).count()
    
    import pytz
    texas_tz = pytz.timezone('US/Central')

    data = []
    for check in checks:
        formatted_amount = f"${check.amount:,.2f}" if check.amount is not None else "$0.00"
        formatted_date = check.check_date.strftime("%Y-%m-%d") if check.check_date else "N/A"
        
        if check.reviewed_at:
            # SQLAlchemy returns naive datetime objects (assumed UTC from DB)
            utc_dt = check.reviewed_at.replace(tzinfo=pytz.UTC)
            texas_dt = utc_dt.astimezone(texas_tz)
            formatted_reviewed_at = texas_dt.strftime("%Y-%m-%d %I:%M:%S %p CT")
        else:
            formatted_reviewed_at = "N/A"

        data.append({
            "Batch Number": batch_number,
            "Date": formatted_date,
            "Store": check.store_name or "N/A",
            "Payee": check.payee or "N/A",
            "Amount": formatted_amount,
            "Bank Name": check.bank or "N/A",
            "Routing Number": check.routing_number or "N/A",
            "Account Number": check.account_number or "N/A",
            "Check Number": check.check_number or "N/A",
            "Memo": check.memo or "N/A",
            "Status": check.status.value,
            "Reviewed By": check.reviewed_by or "Auto",
            "Reviewed At": formatted_reviewed_at
        })
        
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=f"Batch_{batch_number}")
        
        # Auto-adjust column width for readability
        worksheet = writer.sheets[f"Batch_{batch_number}"]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
            
    output.seek(0)
    return output
