from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Float, Date
from sqlalchemy.orm import relationship
from app.database import Base

# Many-to-Many association for Faculty and Subjects they are qualified to teach
faculty_subjects = Table(
    "faculty_subjects",
    Base.metadata,
    Column("faculty_id", Integer, ForeignKey("faculties.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)
)

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="department")
    faculties = relationship("Faculty", back_populates="department")
    subjects = relationship("Subject", back_populates="department")
    class_groups = relationship("ClassGroup", back_populates="department")


class Faculty(Base):
    __tablename__ = "faculties"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    max_hours_per_week = Column(Integer, default=16, nullable=False)
    current_workload = Column(Float, default=0.0, nullable=False) # Total hours currently assigned
    burnout_risk_score = Column(Float, default=0.0, nullable=False) # Calculated by ML model
    leave_balance = Column(Integer, default=15, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="faculty_profile")
    department = relationship("Department", back_populates="faculties")
    qualified_subjects = relationship("Subject", secondary=faculty_subjects, back_populates="qualified_faculties")
    timetable_slots = relationship("TimetableSlot", back_populates="faculty")
    substitute_allocations = relationship("SubstituteAllocation", foreign_keys="[SubstituteAllocation.substitute_id]", back_populates="substitute")


class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    hours_required_per_week = Column(Integer, default=4, nullable=False)
    
    # Relationships
    department = relationship("Department", back_populates="subjects")
    qualified_faculties = relationship("Faculty", secondary=faculty_subjects, back_populates="qualified_subjects")
    timetable_slots = relationship("TimetableSlot", back_populates="subject")


class Classroom(Base):
    __tablename__ = "classrooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    room_number = Column(String, unique=True, index=True, nullable=False)
    capacity = Column(Integer, default=60, nullable=False)
    
    # Relationships
    timetable_slots = relationship("TimetableSlot", back_populates="classroom")


class ClassGroup(Base):
    __tablename__ = "class_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. "CSE-A", "ME-B"
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    department = relationship("Department", back_populates="class_groups")
    timetable_slots = relationship("TimetableSlot", back_populates="class_group")


class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(String, nullable=False) # "Monday", "Tuesday", etc.
    period_number = Column(Integer, nullable=False) # 1 to 8
    
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True)
    class_group_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False)
    
    # Temporary / Special schedules (like exam schedules)
    is_temporary = Column(Boolean, default=False, nullable=False)
    effective_date = Column(Date, nullable=True) # Applicable date for temporary slots
    
    # Relationships
    subject = relationship("Subject", back_populates="timetable_slots")
    faculty = relationship("Faculty", back_populates="timetable_slots")
    classroom = relationship("Classroom", back_populates="timetable_slots")
    class_group = relationship("ClassGroup", back_populates="timetable_slots")
