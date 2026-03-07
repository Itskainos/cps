import pandas as pd
from sqlalchemy.orm import Session
from io import BytesIO
from .models import Check

def generate_accounting_spreadsheet(db: Session, batch_id: int) -> BytesIO:
    """
    Generates accurately formatted PRD 3 Accounting Spreadsheet.
    """
    checks = db.query(Check).filter(Check.batch_id == batch_id).all()
    
    data = []
    for check in checks:
        data.append({
            "Batch ID": check.batch_id,
            "Store": check.store_name,
            "Check Number": check.check_number,
            "Date": check.check_date.strftime("%Y-%m-%d") if check.check_date else None,
            "Payee": check.payee,
            "Amount": check.amount,
            "Memo": check.memo,
            "Bank": check.bank,
            "Status": check.status.value,
            "Reviewed By": check.reviewed_by,
            "Reviewed At": check.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if check.reviewed_at else None
        })
        
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=f"Batch_{batch_id}")
        
        # Auto-adjust column width for readability
        worksheet = writer.sheets[f"Batch_{batch_id}"]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
            
    output.seek(0)
    return output
