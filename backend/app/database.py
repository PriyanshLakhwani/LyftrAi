import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Create engine using DATABASE_URL
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
