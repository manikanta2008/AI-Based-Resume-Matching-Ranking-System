import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Determine SQL echo from environment (default False for maximum performance)
sql_echo = os.getenv("SQL_ECHO", "false").lower() in ("true", "1")

# Create PostgreSQL database engine with connection pooling optimized for concurrent threads
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=15,
    max_overflow=25,
    pool_pre_ping=True,
    echo=sql_echo
)

# Create database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for database models
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()