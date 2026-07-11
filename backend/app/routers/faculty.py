from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import get_current_user, require_any_user
from app.models.user import User
from app.models.schedule import Faculty, TimetableSlot
from app.models.leave import LeaveRequest, SwapRequest, AuditLog
from app.schemas.leave import LeaveResponse, LeaveCreate, SwapResponse, SwapCreate, SwapStatusUpdate
from app.services.nlp_parser import parse_leave_request_text

router = APIRouter(prefix="/api/faculty", tags=["Faculty Operations"])

class TextLeaveRequest(BaseModel):
    text: str

@router.post("/leave-request", response_model=LeaveResponse)
def submit_leave(
    payload: LeaveCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_any_user)
):
    """
    Submits a structured leave request.
    """
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found for this user")
        
    days = (payload.end_date - payload.start_date).days + 1
    if faculty.leave_balance < days:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. You have {faculty.leave_balance} leave days remaining, but requested {days} days."
        )
        
    leave = LeaveRequest(
        faculty_id=faculty.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        specific_periods=payload.specific_periods,
        status="PENDING",
        reason=payload.reason
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    
    return {
        "id": leave.id,
        "faculty_id": leave.faculty_id,
        "faculty_name": current_user.name,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "specific_periods": leave.specific_periods,
        "status": leave.status,
        "reason": leave.reason,
        "approved_by_id": leave.approved_by_id,
        "comments": leave.comments,
        "created_at": leave.created_at
    }

@router.post("/leave-request/nlp")
def parse_and_submit_nlp_leave(
    payload: TextLeaveRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_any_user)
):
    """
    Parses a free-text leave request (Layer 5 NLP-lite) and returns structured values
    or auto-creates a pending request.
    """
    parsed = parse_leave_request_text(payload.text)
    
    # We return the parsed values so the frontend can display and let the user confirm/edit them!
    # This provides a great UX (auto-filled form fields).
    
    # Let's check if they suggested a cover faculty, and try to find their ID
    suggested_faculty_id = None
    if parsed["suggested_cover_faculty"]:
        target_user = db.query(User).filter(User.name.icontains(parsed["suggested_cover_faculty"])).first()
        if target_user:
            fac = db.query(Faculty).filter(Faculty.user_id == target_user.id).first()
            if fac:
                suggested_faculty_id = fac.id
                
    return {
        "start_date": parsed["start_date"].isoformat(),
        "end_date": parsed["end_date"].isoformat(),
        "specific_periods": ",".join(str(p) for p in parsed["periods"]) if parsed["periods"] else None,
        "reason": parsed["reason"],
        "suggested_cover_faculty_name": parsed["suggested_cover_faculty"],
        "suggested_cover_faculty_id": suggested_faculty_id
    }

@router.get("/leaves/my", response_model=List[LeaveResponse])
def get_my_leaves(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        return []
    leaves = db.query(LeaveRequest).filter(LeaveRequest.faculty_id == faculty.id).all()
    
    res = []
    for l in leaves:
        res.append({
            "id": l.id,
            "faculty_id": l.faculty_id,
            "faculty_name": current_user.name,
            "start_date": l.start_date,
            "end_date": l.end_date,
            "specific_periods": l.specific_periods,
            "status": l.status,
            "reason": l.reason,
            "approved_by_id": l.approved_by_id,
            "comments": l.comments,
            "created_at": l.created_at
        })
    return res

@router.post("/swap-request", response_model=SwapResponse)
def submit_swap_request(
    payload: SwapCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_any_user)
):
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    # Check if target faculty exists
    target = db.query(Faculty).filter(Faculty.id == payload.receiver_faculty_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target faculty not found")
        
    # Create Swap Request
    swap = SwapRequest(
        sender_faculty_id=faculty.id,
        receiver_faculty_id=payload.receiver_faculty_id,
        date_a=payload.date_a,
        period_a=payload.period_a,
        date_b=payload.date_b,
        period_b=payload.period_b,
        status="PENDING_RECEIVER",
        reason=payload.reason
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    
    return {
        "id": swap.id,
        "sender_faculty_id": swap.sender_faculty_id,
        "sender_name": current_user.name,
        "receiver_faculty_id": swap.receiver_faculty_id,
        "receiver_name": target.user.name,
        "date_a": swap.date_a,
        "period_a": swap.period_a,
        "date_b": swap.date_b,
        "period_b": swap.period_b,
        "status": swap.status,
        "reason": swap.reason,
        "created_at": swap.created_at
    }

@router.get("/swaps/incoming", response_model=List[SwapResponse])
def get_incoming_swaps(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        return []
        
    swaps = db.query(SwapRequest).filter(
        SwapRequest.receiver_faculty_id == faculty.id,
        SwapRequest.status == "PENDING_RECEIVER"
    ).all()
    
    res = []
    for s in swaps:
        res.append({
            "id": s.id,
            "sender_faculty_id": s.sender_faculty_id,
            "sender_name": s.sender_faculty.user.name,
            "receiver_faculty_id": s.receiver_faculty_id,
            "receiver_name": current_user.name,
            "date_a": s.date_a,
            "period_a": s.period_a,
            "date_b": s.date_b,
            "period_b": s.period_b,
            "status": s.status,
            "reason": s.reason,
            "created_at": s.created_at
        })
    return res

@router.post("/swaps/{swap_id}/respond")
def respond_to_swap(
    swap_id: int, 
    action: SwapStatusUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_any_user)
):
    """
    Called by receiver faculty to confirm or reject.
    If CONFIRMED, routes to HOD for approval (or automatically executes if coordinator/admin).
    """
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
    if not swap or swap.receiver_faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="Swap request not found or unauthorized")
        
    if action.status == "REJECTED":
        swap.status = "REJECTED_RECEIVER"
    elif action.status == "CONFIRMED":
        # If mutual agreement, escalates to HOD
        swap.status = "PENDING_APPROVAL"
    else:
        raise HTTPException(status_code=400, detail="Invalid respond status")
        
    db.commit()
    return {"status": "SUCCESS", "swap_status": swap.status}

@router.get("/substitutions/coverages")
def get_my_substitutions(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    from app.models.leave import SubstituteAllocation
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        return []
        
    substitutions = db.query(SubstituteAllocation).filter(
        SubstituteAllocation.substitute_id == faculty.id,
        SubstituteAllocation.status == "RESOLVED"
    ).all()
    
    res = []
    for s in substitutions:
        res.append({
            "id": s.id,
            "date": s.date,
            "period_number": s.period_number,
            "class_group_name": s.class_group.name if s.class_group else "None",
            "original_faculty_name": s.original_faculty.user.name if s.original_faculty else "None",
            "explanation": s.explanation
        })
    return res

@router.get("/leaves/balance")
def get_leave_balance(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    return {"leave_balance": faculty.leave_balance}

@router.post("/leaves/{leave_id}/cancel")
def cancel_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user)
):
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.faculty_id == faculty.id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
        
    if leave.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Leave is already cancelled")
        
    was_approved = leave.status == "APPROVED"
    leave.status = "CANCELLED"
    
    if was_approved:
        # Restore leave balance
        days = (leave.end_date - leave.start_date).days + 1 if leave.end_date and leave.start_date else 1
        faculty.leave_balance += days
        
        # Cancel any substitute allocations
        from app.models.leave import SubstituteAllocation
        sub_allocs = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.leave_request_id == leave.id
        ).all()
        for alloc in sub_allocs:
            alloc.status = "CANCELLED"
            if alloc.substitute:
                alloc.substitute.current_workload = max(0.0, alloc.substitute.current_workload - 1.0)
                
    db.commit()
    return {"status": "SUCCESS", "message": "Leave cancelled successfully", "leave_balance": faculty.leave_balance}

@router.get("/swaps/my")
def get_my_swaps_history(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    from app.models.leave import SwapRequest
    faculty = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if not faculty:
        return []
        
    swaps = db.query(SwapRequest).filter(
        (SwapRequest.sender_faculty_id == faculty.id) | (SwapRequest.receiver_faculty_id == faculty.id)
    ).order_by(SwapRequest.created_at.desc()).all()
    
    res = []
    for s in swaps:
        res.append({
            "id": s.id,
            "sender_name": s.sender_faculty.user.name,
            "receiver_name": s.receiver_faculty.user.name,
            "date_a": s.date_a,
            "period_a": s.period_a,
            "date_b": s.date_b,
            "period_b": s.period_b,
            "status": s.status,
            "reason": s.reason,
            "created_at": s.created_at,
            "is_sender": s.sender_faculty_id == faculty.id
        })
    return res

@router.get("/swaps/class-counts")
def get_swaps_count_per_class(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    from app.models.leave import SwapRequest
    from app.models.schedule import ClassGroup
    
    approved_swaps = db.query(SwapRequest).filter(SwapRequest.status == "APPROVED").all()
    class_counts = {}
    
    for s in approved_swaps:
        day_str = s.date_a.strftime("%A")
        slot = db.query(TimetableSlot).filter(
            TimetableSlot.faculty_id == s.sender_faculty_id,
            TimetableSlot.day_of_week == day_str,
            TimetableSlot.period_number == s.period_a,
            TimetableSlot.is_temporary == False
        ).first()
        if slot and slot.class_group:
            class_name = slot.class_group.name
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
    # Include all classes for comprehensive report list
    all_classes = db.query(ClassGroup).all()
    for c in all_classes:
        if c.name not in class_counts:
            class_counts[c.name] = 0
            
    return [{"class_name": k, "count": v} for k, v in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)]

