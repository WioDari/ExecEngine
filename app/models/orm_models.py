# app/models/orm_models.py

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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

    id = Column(Integer, primary_key=True, index=True)
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submissions = relationship("SubmissionModel", back_populates="batch")

class SubmissionModel(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), unique=True, nullable=False, index=True)
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    source_code = Column(Text, nullable=False)
    stdin = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=True)
    compile_output = Column(Text, nullable=True)
    compiler_options = Column(String(255), nullable=True)
    command_line_args = Column(String(255), nullable=True)
    time = Column(Integer, default=0, nullable=False)
    memory = Column(Integer, default=0, nullable=False)
    time_limit = Column(Integer, default=2000, nullable=False)
    memory_limit = Column(Integer, default=128000, nullable=False)
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)
    exit_signal = Column(Integer, nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    language = relationship("LanguageModel", back_populates="submissions")
    status = relationship("StatusModel", back_populates="submissions")
    batch = relationship("BatchModel", back_populates="submissions")
    user = relationship("UserModel", back_populates="submissions")
