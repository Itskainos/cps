
import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv(r"c:\Users\Kainos\Documents\Quicktrackinc\CPS\.env.local")

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)

def check_batch_by_number(target_num):
    with engine.connect() as conn:
        # Get all batches to find the one with index target_num
        all_batches_query = text("SELECT id FROM check_batches ORDER BY id ASC")
        all_ids = [row[0] for row in conn.execute(all_batches_query).fetchall()]
        
        if target_num > len(all_ids) or target_num < 1:
            print(f"Batch Number {target_num} not found (Total batches: {len(all_ids)})")
            return

        batch_id = all_ids[target_num - 1]
        print(f"Batch Number {target_num} corresponds to Batch ID {batch_id}")

        # Check batch status
        batch_query = text("SELECT id, status, created_by, created_at, parameters_json FROM check_batches WHERE id = :batch_id")
        batch = conn.execute(batch_query, {"batch_id": batch_id}).fetchone()
        
        print(f"--- Batch {batch_id} (Number {target_num}) ---")
        print(f"Status: {batch.status}")
        print(f"Created By: {batch.created_by}")
        print(f"Created At: {batch.created_at}")
        print(f"PDF Path: {batch.original_pdf_path}")
        if batch.original_pdf_path and os.path.exists(batch.original_pdf_path):
            print("PDF file exists on disk.")
        else:
            print("PDF file MISSING from disk.")
        check_query = text("SELECT status, count(*) FROM checks WHERE batch_id = :batch_id GROUP BY status")
        checks = conn.execute(check_query, {"batch_id": batch_id}).fetchall()
        
        print("\n--- Checks Summary ---")
        if not checks:
            print("No checks found for this batch (UI will show 'Processing...')")
        else:
            for row in checks:
                print(f"Status {row.status}: {row.count} checks")

if __name__ == "__main__":
    check_batch_by_number(4)
