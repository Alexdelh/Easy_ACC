from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, JSON, DateTime, LargeBinary, ForeignKey, func, Text
from datetime import datetime
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    current_phase: Mapped[Optional[str]] = mapped_column(String)
    state_data: Mapped[dict] = mapped_column(JSON, default={})
    owner_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Future-proofing
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship to datasets
    datasets: Mapped[List["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'production_curve', 'consumption_profile'
    
    # Validation logic can happen in service layer, but we store file type here
    file_type: Mapped[str] = mapped_column(String, nullable=False) # csv, xlsx, txt
    
    # Store data as JSON for structured data or serialization results
    # Use LargeBinary if storing raw file bytes is needed, but current app uses JSON/Dicts mainly.
    # However, to support "Gatekeeper" and potential raw files, structured data is better stored as JSON if possible.
    # If the app stores serialized pandas DF, that is a Dict.
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    metadata_info: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    project: Mapped["Project"] = relationship(back_populates="datasets")
