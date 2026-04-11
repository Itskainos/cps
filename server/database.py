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

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 60,  # Recycle faster to avoid stale SSL connections
    "pool_timeout": 30,  # Wait up to 30s for a connection
}

if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    **engine_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
