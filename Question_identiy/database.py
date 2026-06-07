from sqlalchemy import create_engine

# SQLite for now (easy)
DATABASE_URL = "sqlite:///./questions.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)