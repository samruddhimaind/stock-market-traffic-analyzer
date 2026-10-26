from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite Database File URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./stock_app.db"

# Engine setup (check_same_thread=False SQLite ke liye zaroori hai)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI Dependency for Database Session Handling"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()