import os
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('../.env.local')

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    row = conn.execute(text("SELECT id, s3_image_url, check_number FROM checks ORDER BY id ASC LIMIT 1")).fetchone()
    url = row[1]
    print("Oldest Check URL:", url)
    print("URL:", url)
    res = requests.get(url)
    print("Status:", res.status_code)
    print("Body:", res.text[:200])
