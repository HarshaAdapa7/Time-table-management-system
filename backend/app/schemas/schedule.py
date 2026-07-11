from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int
    class Config:
        from_attributes = True

class ClassroomBase(BaseModel):
    name: str
    room_number: str
    capacity: int

class ClassroomCreate(ClassroomBase):
    pass

class ClassroomResponse(ClassroomBase):
    id: int
    class Config:
        from_attributes = True

class SubjectBase(BaseModel):
    code: str
    name: str
    department_id: Optional[int] = None
    hours_required_per_week: int = 4

class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int
    class Config:
        from_attributes = True

class ClassGroupBase(BaseModel):
    name: str
    department_id: Optional[int] = None

class ClassGroupCreate(ClassGroupBase):
    pass

class ClassGroupResponse(ClassGroupBase):
    id: int
    class Config:
        from_attributes = True

class FacultyBase(BaseModel):
    max_hours_per_week: int = 16

class FacultyCreate(FacultyBase):
    user_id: int
    department_id: Optional[int] = None
    qualified_subject_ids: List[int] = []

class FacultyResponse(FacultyBase):
    id: int
    user_id: int
    department_id: Optional[int] = None
    current_workload: float
    burnout_risk_score: float
    name: str
    email: str
    department_name: Optional[str] = None
    qualified_subjects: List[SubjectResponse] = []
    
    class Config:
        from_attributes = True

class TimetableSlotResponse(BaseModel):
    id: int
    day_of_week: str
    period_number: int
    subject_code: str
    subject_name: str
    faculty_name: str
    classroom_name: Optional[str] = None
    classroom_number: Optional[str] = None
    class_group_name: str
    is_temporary: bool
    effective_date: Optional[date] = None
    is_substitution: Optional[bool] = False
    
    class Config:
        from_attributes = True

class TimetableSlotEdit(BaseModel):
    class_group_id: int
    day_of_week: str
    period_number: int
    new_faculty_id: int
