# app/models/orm_models.py

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, server_default=true(), nullable=False)
    created_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    privileged_user = Column(Boolean, default=False, server_default=false(), nullable=False)

    api_tokens = relationship("ApiTokenModel", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("SubmissionModel", back_populates="user")

class ApiTokenModel(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("UserModel", back_populates="api_tokens")

class StatusModel(Base):
    __tablename__ = "statuses"

    id = Column(Integer, primary_key=True, index=True)
    status_code = Column(String(2), nullable=False)
    status_full = Column(String(25), nullable=False)

    submissions = relationship("SubmissionModel", back_populates="status")

class LanguageModel(Base):
    __tablename__ = "languages"
    __table_args__ = (UniqueConstraint("slug", name="uq_languages_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(64), nullable=False, index=True)
    pool = Column(String(32), nullable=False, default="full", server_default="full")
    enabled = Column(Boolean, nullable=False, default=True, server_default=true())
    name = Column(String(50), nullable=False)
    version = Column(String(25), nullable=False)
    source_file = Column(String(25), nullable=False)
    compiled_file = Column(String(25), nullable=True)
    compile_cmd = Column(Text, nullable=True)
    run_cmd = Column(Text, nullable=False)

    submissions = relationship("SubmissionModel", back_populates="language")

class BatchModel(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_token = Column(String(36), unique=True, nullable=False)
    created_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    submissions = relationship("SubmissionModel", back_populates="batch")


class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(String(128), primary_key=True)
    hostname = Column(String(255), nullable=False)
    pool = Column(String(32), nullable=False)
    version = Column(String(32), nullable=False)
    concurrency = Column(Integer, nullable=False)
    active_jobs = Column(Integer, default=0, server_default="0", nullable=False)
    started_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    last_seen_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False, index=True
    )
    completed_jobs = Column(Integer, default=0, server_default="0", nullable=False)
    failed_jobs = Column(Integer, default=0, server_default="0", nullable=False)
    isolate_version = Column(String(64), nullable=True)
    capabilities_json = Column(Text, nullable=True)

class SubmissionModel(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True) #Response
    token = Column(String(36), unique=True, nullable=False, index=True) #Response
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=False) #Create
    source_code = Column(Text, nullable=False) #Create/Response
    stdin = Column(Text, nullable=True) #Create/Response
    stdout = Column(Text, nullable=True) #Response
    stderr = Column(Text, nullable=True) #Response
    expected_output = Column(Text, nullable=True) #Create/Response
    compile_output = Column(Text, nullable=True) #Response
    compiler_options = Column(String(255), nullable=True) #Create/Response
    command_line_args = Column(String(255), nullable=True) #Create/Response
    time = Column(Float, default=0, server_default="0", nullable=False) #Response
    wall_time = Column(Float, default=0, server_default="0", nullable=False) #Response
    memory = Column(Integer, default=0, server_default="0", nullable=False) #Reponse
    time_limit = Column(Float, default=2, server_default="2", nullable=False) #Create
    extra_time = Column(Float, default=0.5, server_default="0.5", nullable=True) #Create
    wall_time_limit = Column(Float, default=3, server_default="3", nullable=False) #Create
    memory_limit = Column(Integer, default=128000, server_default="128000", nullable=False) #Create
    stack_size = Column(Integer, default=64000, server_default="64000", nullable=True) #Create
    redirect_stderr_to_stdout = Column(Boolean, default=False, server_default=false(), nullable=False) #Create
    enable_network = Column(Boolean, default=False, server_default=false(), nullable=False) #Create
    max_file_size = Column(Integer, default=1024, server_default="1024", nullable=False) #Create
    additional_files = Column(Text, nullable=True) #Create/Response
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=False) #Response
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False) #Response
    finished_at = Column(DateTime, nullable=True) #Response
    exit_code = Column(Integer, nullable=True) #Response
    exit_signal = Column(Integer, nullable=True) #Response
    callback_url = Column(Text, nullable=True) #Create/Response
    worker_id = Column(String(128), nullable=True, index=True)
    attempt_count = Column(Integer, default=0, server_default="0", nullable=False)
    processing_started_at = Column(DateTime, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    language = relationship("LanguageModel", back_populates="submissions")
    status = relationship("StatusModel", back_populates="submissions")
    batch = relationship("BatchModel", back_populates="submissions")
    user = relationship("UserModel", back_populates="submissions")
    callback_deliveries = relationship("CallbackDeliveryModel",back_populates="submission",cascade="all, delete-orphan")

class CallbackDeliveryModel(Base):
    __tablename__ = "callback_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "event_type",
            name="uq_callback_deliveries_submission_event",
        ),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String(36), unique=True, nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    
    event_type = Column(
        String(64), nullable=False, default="submission.completed", server_default="submission.completed"
    )
    callback_url = Column(Text, nullable=False)
    
    status = Column(String(16), nullable=False, default="pending", server_default="pending") # "pending | processing | delivered | retry | failed"
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    locked_by = Column(String(128), nullable=True, index=True)
    lock_token = Column(String(36), nullable=True, unique=True, index=True)
    locked_until = Column(DateTime, nullable=True, index=True)
    
    last_http_status = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    delivered_at = Column(DateTime, nullable=True)
    
    submission = relationship("SubmissionModel", back_populates="callback_deliveries")
