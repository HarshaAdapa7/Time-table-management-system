from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Comma-separated list of periods if partial day (e.g. "3,4") or empty/null for full day
    specific_periods = Column(String, nullable=True) 
    
    status = Column(String, default="PENDING", nullable=False) # PENDING, APPROVED, REJECTED
    reason = Column(Text, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    faculty = relationship("Faculty", foreign_keys=[faculty_id])
    approver = relationship("User", foreign_keys=[approved_by_id])
    substitute_allocations = relationship("SubstituteAllocation", back_populates="leave_request", cascade="all, delete-orphan")


class SubstituteAllocation(Base):
    __tablename__ = "substitute_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    period_number = Column(Integer, nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id", ondelete="CASCADE"), nullable=False)
    original_faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    
    # Can be null if solver fails to find any candidate and leaves period vacant
    substitute_id = Column(Integer, ForeignKey("faculties.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String, default="RESOLVED", nullable=False) # RESOLVED, UNRESOLVED, MANUAL
    explanation = Column(Text, nullable=True) # Reason/Score details or conflict description
    
    # Relationships
    leave_request = relationship("LeaveRequest", back_populates="substitute_allocations")
    substitute = relationship("Faculty", foreign_keys=[substitute_id], back_populates="substitute_allocations")
    original_faculty = relationship("Faculty", foreign_keys=[original_faculty_id])
    class_group = relationship("ClassGroup")


class SwapRequest(Base):
    __tablename__ = "swap_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    receiver_faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    
    # Details of Slot A (belonging to sender)
    date_a = Column(Date, nullable=False)
    period_a = Column(Integer, nullable=False)
    
    # Details of Slot B (belonging to receiver, if mutual swap, else empty if single coverage)
    date_b = Column(Date, nullable=True)
    period_b = Column(Integer, nullable=True)
    
    status = Column(String, default="PENDING_RECEIVER", nullable=False) 
    # PENDING_RECEIVER, REJECTED_RECEIVER, PENDING_APPROVAL (HOD), APPROVED, REJECTED_HOD
    
    reason = Column(Text, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sender_faculty = relationship("Faculty", foreign_keys=[sender_faculty_id])
    receiver_faculty = relationship("Faculty", foreign_keys=[receiver_faculty_id])
    approver = relationship("User", foreign_keys=[approved_by_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False) # LEAVE_APPROVE, SWAP_APPROVE, BASE_GENERATION, MANUAL_EDIT
    details = Column(Text, nullable=False)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    actor = relationship("User")
