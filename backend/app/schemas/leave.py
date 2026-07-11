from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    specific_periods: Optional[str] = None # e.g. "3,4" or null/empty
    reason: Optional[str] = None

class LeaveResponse(BaseModel):
    id: int
    faculty_id: int
    faculty_name: str
    start_date: date
    end_date: date
    specific_periods: Optional[str] = None
    status: str
    reason: Optional[str] = None
    approved_by_id: Optional[int] = None
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LeaveStatusUpdate(BaseModel):
    status: str # APPROVED or REJECTED
    comments: Optional[str] = None

class SubstituteAllocationResponse(BaseModel):
    id: int
    leave_request_id: int
    date: date
    period_number: int
    class_group_name: str
    original_faculty_name: str
    substitute_name: Optional[str] = None
    status: str
    explanation: Optional[str] = None

    class Config:
        from_attributes = True

class SwapCreate(BaseModel):
    receiver_faculty_id: int
    date_a: date
    period_a: int
    date_b: Optional[date] = None
    period_b: Optional[int] = None
    reason: Optional[str] = None

class SwapResponse(BaseModel):
    id: int
    sender_faculty_id: int
    sender_name: str
    receiver_faculty_id: int
    receiver_name: str
    date_a: date
    period_a: int
    date_b: Optional[date] = None
    period_b: Optional[int] = None
    status: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SwapStatusUpdate(BaseModel):
    status: str # APPROVED, REJECTED, or CONFIRMED (if mutual recipient confirm)
    
class NLPParsingRequest(BaseModel):
    text: str

class NLPParsingResponse(BaseModel):
    start_date: date
    end_date: date
    periods: Optional[List[int]] = None
    reason: str
    suggested_cover_faculty: Optional[str] = None
