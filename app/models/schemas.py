# app/models/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

# Пользователь
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

# Токены
class TokenData(BaseModel):
    token: str

class AuthResponse(BaseModel):
    valid: bool
    user_id: Optional[int] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Языки
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

# Статусы
class Status(BaseModel):
    id: int
    status_code: str
    status_full: str

    class Config:
        orm_mode = True

# Отправки
class SubmissionCreate(BaseModel):
    language_id: int
    source_code: str  # Base64
    stdin: Optional[str] = None  # Base64
    expected_output: Optional[str] = None  # Base64
    compiler_options: Optional[str] = None
    command_line_args: Optional[str] = None
    time_limit: Optional[int] = 2000
    memory_limit: Optional[int] = 128000

class SubmissionResponse(BaseModel):
    token: str
    status_id: int
    created_at: datetime
    finished_at: Optional[datetime] = None
    time: Optional[int] = None
    memory: Optional[int] = None
    exit_code: Optional[int] = None
    exit_signal: Optional[int] = None
    stdout: Optional[str] = None  # Base64
    stderr: Optional[str] = None  # Base64
    compile_output: Optional[str] = None  # Base64

    class Config:
        orm_mode = True

class BatchSubmissionCreate(BaseModel):
    submissions: List[SubmissionCreate]

class BatchSubmissionResponse(BaseModel):
    batch_token: str
    submission_tokens: List[str]

class ServerConfiguration(BaseModel):
    configuration: Dict[str, str]

    class Config:
        orm_mode = True
