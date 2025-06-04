# app/models/orm_models.py

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float
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
    privileged_user = Column(Boolean, default=False, nullable=False)

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
    time = Column(Float, default=0, nullable=False) #Response
    wall_time = Column(Float, default=0, nullable=False) #Response
    memory = Column(Integer, default=0, nullable=False) #Reponse
    time_limit = Column(Float, default=2, nullable=False) #Create
    extra_time = Column(Float, default=0.5, nullable=True) #Create
    wall_time_limit = Column(Float, default=3, nullable=False) #Create
    memory_limit = Column(Integer, default=128000, nullable=False) #Create
    stack_size = Column(Integer, default=64000, nullable=True) #Create
    redirect_stderr_to_stdout = Column(Boolean, default=False, nullable=False) #Create
    enable_network = Column(Boolean, default=False, nullable=False) #Create
    max_file_size = Column(Integer, default=1024, nullable=False) #Create
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=False) #Response
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False) #Response
    finished_at = Column(DateTime, nullable=True) #Response
    exit_code = Column(Integer, nullable=True) #Response
    exit_signal = Column(Integer, nullable=True) #Response
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    language = relationship("LanguageModel", back_populates="submissions")
    status = relationship("StatusModel", back_populates="submissions")
    batch = relationship("BatchModel", back_populates="submissions")
    user = relationship("UserModel", back_populates="submissions")
