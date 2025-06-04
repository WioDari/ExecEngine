# app/models/schemas.py

from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field, conint, confloat, validator
from datetime import datetime
from app.core.config import settings

# User
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

# Tokens
class TokenData(BaseModel):
    token: str

class AuthResponse(BaseModel):
    valid: bool
    user_id: Optional[int] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Programming Languages
class Language(BaseModel):
    id: int
    name: str
    version: str
    source_file: str
    compiled_file: Optional[str] = None
    compile_cmd: Optional[str] = None
    run_cmd: str

    class Config:
        orm_mode = True

# Statuses
class Status(BaseModel):
    id: int
    status_code: str
    status_full: str

    class Config:
        orm_mode = True

# Submissions
class SubmissionBase(BaseModel):
    language_id: conint(gt=0)
    source_code: str
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
    compiler_options: Optional[str] = None
    command_line_args: Optional[str] = None
    time_limit: confloat(gt=0, le=settings.MAX_TIME_LIMIT) = Field(2.0)
    extra_time: confloat(ge=0, le=settings.MAX_EXTRA_TIME) = Field(0.5)
    wall_time_limit: confloat(gt=0, le=settings.MAX_WALL_TIME_LIMIT) = Field(3.0)
    memory_limit: conint(gt=0, le=settings.MAX_MEMORY_LIMIT) = Field(128_000)
    stack_size: conint(gt=0, le=settings.MAX_STACK_SIZE) = Field(64_000)
    max_file_size: conint(gt=0, le=settings.MAX_FILE_SIZE) = Field(1_024)

    redirect_stderr_to_stdout: bool = False
    enable_network: bool = False
    
    @validator("compiler_options")
    def _check_compiler_opts(cls, v):
        if v is not None and not settings.ALLOW_COMPILER_OPTIONS:
            raise ValueError("Compiler options are disabled by server settings")
        return v

    @validator("command_line_args")
    def _check_cmd_args(cls, v):
        if v is not None and not settings.ALLOW_COMMAND_LINE_ARGS:
            raise ValueError("Command-line args are disabled by server settings")
        return v

    @validator("enable_network")
    def _check_network(cls, v):
        if v and not settings.ALLOW_ENABLE_NETWORK:
            raise ValueError("Network access is disabled by server settings")
        return v

    class Config:
        anystr_strip_whitespace = True
        min_anystr_length = 1

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionResponse(BaseModel):
    token: str
    status_id: int
    created_at: datetime
    finished_at: Optional[datetime] = None
    time: Optional[float] = None
    wall_time: Optional[float] = None
    memory: Optional[int] = None
    exit_code: Optional[int] = None
    exit_signal: Optional[int] = None
    stdout: Optional[str] = None  # Base64
    stderr: Optional[str] = None  # Base64
    compile_output: Optional[str] = None  # Base64
    source_code: str  # Base64
    stdin: Optional[str] = None  # Base64
    expected_output: Optional[str] = None  # Base64
    compiler_options: Optional[str] = None
    command_line_args: Optional[str] = None

    class Config:
        orm_mode = True

class BatchSubmissionCreate(BaseModel):
    submissions: List[SubmissionCreate]
    
    @validator("submissions")
    def check_batch_size(cls, v):
        if len(v) > settings.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size > {settings.MAX_BATCH_SIZE}")
        return v

class BatchSubmissionResponse(BaseModel):
    batch_token: str
    submission_tokens: List[str]
    results: Optional[List[SubmissionResponse]] = None

class ServerConfiguration(BaseModel):
    configuration: Dict[str, str]

    class Config:
        orm_mode = True

class SoftwareConfiguration(BaseModel):
    max_concurent_submissions: int
    default_time_limit: int
    default_memory_limit: int
    default_extra_time: float
    default_wall_time_limit: int
    default_stack_size: int
    default_max_file_size: int
    max_time_limit: int
    max_memory_limit: int
    max_extra_time: float
    max_wall_time_limit: int
    max_stack_size: int
    max_file_size: int
    allow_enable_network: bool
    always_redirect_stderr_to_stdout: bool
    allow_command_line_args: bool
    allow_compiler_options: bool
    
    class Config:
        orm_mode = True