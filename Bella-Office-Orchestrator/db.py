from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# simple SQLite in your project folder
DATABASE_URL = "sqlite:///./worklogs.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
