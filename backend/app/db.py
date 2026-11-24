from sqlalchemy import create_engine, Column, String, JSON, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from .common import env

engine = create_engine(env("DATABASE_URL", "sqlite:///./familycheck.db"))
Session = sessionmaker(engine)
Base = declarative_base()

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(String, primary_key=True)
    title = Column(String)
    status = Column(String, default="queued")   # queued | running | done | failed
    progress = Column(Float, default=0)
    message = Column(String, default="")
    metadata_ = Column("metadata", JSON)
    modules = Column(JSON)
    verdict = Column(JSON)
    created = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)
