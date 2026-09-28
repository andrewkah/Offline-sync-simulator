from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, DateTime, Integer, String, create_engine

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# the model class
class PDPModel(Base):
    __tablename__ = "pdp_data"

    id = Column(String, primary_key=True, index=True)
    urban_council = Column(String, index=True)
    pdp_status = Column(
        String,
    )
    expiry_year = Column(Integer, nullable=True)
    field_officer_timestamp = Column(DateTime, index=True)
    committed_at = Column(DateTime)
