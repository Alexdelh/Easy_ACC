import os
import json
from datetime import datetime
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from services.models import Base, Project, Dataset
from services.state_serializer import serialize_state, deserialize_state

# Exception for Gatekeeper
class UnsupportedFileTypeError(Exception):
    pass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create Engine
# maintain a single engine instance
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the SQLite database and create tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Project Services ---

def save_project(name: str, current_phase: str, state_dict: dict, project_id: int = None) -> int:
    """
    Save or update a project atomically.
    Returns the project ID.
    """
    session = SessionLocal()
    try:
        if project_id:
            project = session.get(Project, project_id)
            if not project:
                # Fallback: try finding by name if ID was provided but not found (edge case)
                project = session.scalar(select(Project).where(Project.name == name))
        else:
            project = session.scalar(select(Project).where(Project.name == name))

        if project:
            project.current_phase = current_phase
            project.state_data = state_dict
            # updated_at handled by onupdate in model, but we can force it
            project.updated_at = datetime.now()
        else:
            project = Project(name=name, current_phase=current_phase, state_data=state_dict)
            session.add(project)

        session.commit()
        session.refresh(project)
        return project.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def load_project(project_id: int):
    """Load a project by ID."""
    session = SessionLocal()
    try:
        project = session.get(Project, project_id)
        if project:
            return {
                "id": project.id,
                "name": project.name,
                "current_phase": project.current_phase,
                "state_data": project.state_data,
                "updated_at": project.updated_at
            }
        return None
    finally:
        session.close()

def list_projects():
    """List all projects."""
    session = SessionLocal()
    try:
        stmt = select(Project).order_by(Project.updated_at.desc())
        projects = session.scalars(stmt).all()
        return [
            {"id": p.id, "name": p.name, "updated_at": p.updated_at, "current_phase": p.current_phase}
            for p in projects
        ]
    finally:
        session.close()

def delete_project(project_id: int):
    """Delete a project and its datasets (Cascade)."""
    session = SessionLocal()
    try:
        project = session.get(Project, project_id)
        if project:
            session.delete(project)
            session.commit()
    finally:
        session.close()

# --- Dataset Services ---

def validate_file_type(filename_or_type: str):
    """
    Gatekeeper: Restrict to .csv, .txt, .xlsx or known internal types.
    If 'type' is passed (like 'production_curve'), we check usage context or assume it's valid if internal.
    The user requirement was specific to 'uploads'.
    """
    # Allowed extensions/types
    ALLOWED_EXTENSIONS = {'.csv', '.txt', '.xlsx'}
    
    # Check if it looks like a filename
    if "." in filename_or_type:
        ext = os.path.splitext(filename_or_type)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"File type '{ext}' is not supported. Allowed: {ALLOWED_EXTENSIONS}")

def save_dataset(project_id: int, name: str, type: str, data: dict, metadata: dict = None, file_type: str = "json"):
    """
    Save a dataset linked to a project using an Atomic Transaction.
    Updates the project's 'updated_at' timestamp automatically via relationship touch or explicit update.
    """
    # 1. Gatekeeper Validation
    # Use default 'json' for internal data structures, check file_type if it's a file upload
    if file_type != "json":
        validate_file_type(f"test.{file_type}") # Simple check, or relax if file_type is extension

    session = SessionLocal()
    try:
        # Atomic Transaction Context
        project = session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # Calculate Size (Estimate JSON size) after first creating a serializable snapshot
        serializable_data = serialize_state(data)
        data_json_str = json.dumps(serializable_data)
        size_bytes = len(data_json_str.encode('utf-8'))

        # Check if dataset exists for this project and name
        stmt = select(Dataset).where(Dataset.project_id == project_id, Dataset.name == name)
        dataset = session.scalar(stmt)

        if dataset:
            dataset.type = type
            dataset.data = serializable_data
            dataset.metadata_info = metadata
            dataset.file_type = file_type
            dataset.size_bytes = size_bytes
            # dataset.created_at is fixed, maybe add updated_at to dataset model if needed
        else:
            dataset = Dataset(
                project_id=project_id,
                name=name,
                type=type,
                data=serializable_data,
                metadata_info=metadata,
                file_type=file_type,
                size_bytes=size_bytes
            )
            session.add(dataset)

        # Atomic State Management: Update Project Timestamp to reflect activity
        project.updated_at = datetime.now()
        
        session.commit()
        return dataset.id
    except IntegrityError:
        session.rollback()
        raise ValueError("Database constraint error.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def list_datasets(project_id: int, dataset_type: str = None):
    """List datasets for a specific project."""
    session = SessionLocal()
    try:
        stmt = select(Dataset).where(Dataset.project_id == project_id)
        if dataset_type:
            stmt = stmt.where(Dataset.type == dataset_type)
        stmt = stmt.order_by(Dataset.created_at.desc())
        datasets = session.scalars(stmt).all()
        return [
            {"id": d.id, "name": d.name, "type": d.type, "created_at": d.created_at, "size_bytes": d.size_bytes}
            for d in datasets
        ]
    finally:
        session.close()

def load_dataset(dataset_id: int):
    """Load a dataset by ID."""
    session = SessionLocal()
    try:
        dataset = session.get(Dataset, dataset_id)
        if dataset:
            return {
                "id": dataset.id,
                "project_id": dataset.project_id,
                "name": dataset.name,
                "type": dataset.type,
                "data": deserialize_state(dataset.data),
                "metadata": dataset.metadata_info,
                "file_type": dataset.file_type
            }
        return None
    finally:
        session.close()

def delete_dataset(dataset_id: int):
    """Delete a dataset."""
    session = SessionLocal()
    try:
        dataset = session.get(Dataset, dataset_id)
        if dataset:
            session.delete(dataset)
            session.commit()
    finally:
        session.close()

def get_storage_usage():
    """Calculate total storage used by datasets."""
    session = SessionLocal()
    try:
        total_bytes = session.scalar(select(func.sum(Dataset.size_bytes)))
        return total_bytes if total_bytes else 0
    finally:
        session.close()
