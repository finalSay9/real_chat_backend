from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://fastapi:fastapi123@postgres:5432/fastapi_db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base=declarative_base()

async def init_db():
    """Create all tables on startup."""
    def init_db():
        """Create all tables on startup."""
        Base.metadata.create_all(bind=engine)
    