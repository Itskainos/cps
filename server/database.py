import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env.local if it exists
# We check parent dir because api/ is a subdirectory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local"))

# Expect DATABASE_URL from environment
# Fallback to local SQLite for development purposes
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Postgres requires the uri to start with postgresql://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True,      # Important for Neon/Serverless DBs
    pool_recycle=300,        # Refresh connections every 5 mins
    pool_size=5,             # Small pool is better for serverless
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
