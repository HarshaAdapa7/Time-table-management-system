from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth.dependencies import require_hod
from app.models.user import User
from app.models.schedule import Faculty, Department, TimetableSlot, Subject
from app.models.leave import LeaveRequest, SubstituteAllocation, AuditLog
from app.schemas.leave import LeaveResponse, LeaveStatusUpdate, SubstituteAllocationResponse
from app.services.solver import resolve_leave_substitutions
from app.utils.explainability import explain_substitution_conflict

router = APIRouter(prefix="/api/hod", tags=["HOD Operations"], dependencies=[Depends(require_hod)])

@router.get("/leaves/pending", response_model=List[LeaveResponse])
def get_pending_leaves(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns pending leaves in the HOD's department (or all departments if Admin).
    """
    query = db.query(LeaveRequest).filter(LeaveRequest.status == "PENDING")
    
    if current_user.role == "HOD":
        # Scoped to HOD's department
        query = query.join(Faculty, LeaveRequest.faculty_id == Faculty.id).filter(
            Faculty.department_id == current_user.department_id
        )
        
    leaves = query.all()
    # Map model to response schema fields manually to resolve faculty name
    res = []
    for l in leaves:
        res.append({
            "id": l.id,
            "faculty_id": l.faculty_id,
            "faculty_name": l.faculty.user.name,
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

@router.post("/leaves/{leave_id}/action")
def take_leave_action(
    leave_id: int, 
    action: LeaveStatusUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_hod)
):
    """
    Approves or rejects a leave request. If approved, triggers the local re-optimizer solver
    to find substitutes.
    """
    leave_req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
        
    # Check HOD department scope
    if current_user.role == "HOD" and leave_req.faculty.department_id != current_user.department_id:
        raise HTTPException(
            status_code=403, 
            detail="Forbidden: Cannot approve leave requests for other departments"
        )
        
    leave_req.status = action.status
    leave_req.comments = action.comments
    leave_req.approved_by_id = current_user.id
    
    # If approved, run solver to find substitute teachers
    solver_results = None
    if action.status == "APPROVED":
        days = (leave_req.end_date - leave_req.start_date).days + 1 if leave_req.end_date and leave_req.start_date else 1
        if leave_req.faculty.leave_balance < days:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve. Faculty member only has {leave_req.faculty.leave_balance} leave days remaining, but requested {days} days."
            )
        leave_req.faculty.leave_balance -= days
        db.commit()
        solver_results = resolve_leave_substitutions(db, leave_id)
    else:
        db.commit()
        
    return {
        "status": "SUCCESS",
        "leave_status": action.status,
        "solver_results": solver_results
    }

@router.get("/leaves/active")
def get_active_leaves(date_str: str, db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns a list of faculty on leave for the given date, and how many substitution slots they needed.
    """
    from datetime import datetime
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")
        
    query = db.query(LeaveRequest).filter(
        LeaveRequest.status == "APPROVED",
        LeaveRequest.start_date <= target_date,
        LeaveRequest.end_date >= target_date
    )
    
    if current_user.role == "HOD":
        query = query.join(Faculty, LeaveRequest.faculty_id == Faculty.id).filter(
            Faculty.department_id == current_user.department_id
        )
        
    leaves = query.all()
    results = []
    
    for l in leaves:
        # Check SubstituteAllocation table for this date to see how many slots were needed
        allocs = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.leave_request_id == l.id,
            SubstituteAllocation.date == target_date
        ).all()
        
        resolved = sum(1 for a in allocs if a.status == "RESOLVED")
        total = len(allocs)
        
        substitutes = []
        for a in allocs:
            sub_name = "None"
            if a.substitute_id:
                sub_fac = db.query(Faculty).get(a.substitute_id)
                if sub_fac:
                    sub_name = sub_fac.user.name
            substitutes.append({
                "period": a.period_number,
                "class_name": a.class_group.name,
                "substitute_name": sub_name,
                "status": a.status
            })
            
        results.append({
            "leave_id": l.id,
            "faculty_name": l.faculty.user.name,
            "faculty_email": l.faculty.user.email,
            "reason": l.reason,
            "specific_periods": l.specific_periods,
            "total_slots_missed": total,
            "slots_resolved": resolved,
            "substitutes": substitutes
        })
        
    return results

@router.get("/substitutions/unresolved", response_model=List[SubstituteAllocationResponse])
def get_unresolved_substitutions(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Lists unresolved periods for classes within the HOD's department.
    """
    query = db.query(SubstituteAllocation).filter(SubstituteAllocation.status == "UNRESOLVED")
    if current_user.role == "HOD":
        query = query.join(Faculty, SubstituteAllocation.original_faculty_id == Faculty.id).filter(
            Faculty.department_id == current_user.department_id
        )
        
    allocations = query.all()
    res = []
    for a in allocations:
        # Find original slot to get subject_id
        slot = db.query(TimetableSlot).filter(
            TimetableSlot.faculty_id == a.original_faculty_id,
            TimetableSlot.day_of_week == a.date.strftime("%A"),
            TimetableSlot.period_number == a.period_number,
            TimetableSlot.is_temporary == False
        ).first()
        
        if slot:
            exp = explain_substitution_conflict(
                db, 
                slot.subject_id,
                a.date.strftime("%A"),
                a.period_number,
                a.date
            )
        else:
            exp = "Original weekly slot not found in base timetable."
            
        res.append({
            "id": a.id,
            "leave_request_id": a.leave_request_id,
            "date": a.date,
            "period_number": a.period_number,
            "class_group_name": a.class_group.name,
            "original_faculty_name": a.original_faculty.user.name,
            "substitute_name": None,
            "status": a.status,
            "explanation": exp
        })
    return res

@router.post("/substitutions/{alloc_id}/override")
def manual_substitution_override(
    alloc_id: int,
    substitute_faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hod)
):
    """
    Allows HOD to manually force a substitute teacher for an unresolved period.
    """
    alloc = db.query(SubstituteAllocation).filter(SubstituteAllocation.id == alloc_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Substitute allocation not found")
        
    # Check HOD department scope
    if current_user.role == "HOD" and alloc.original_faculty.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot override substitutions for other departments")
        
    sub = db.query(Faculty).filter(Faculty.id == substitute_faculty_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitute faculty not found")
        
    # Update allocation
    alloc.substitute_id = sub.id
    alloc.status = "MANUAL"
    alloc.explanation = f"Manual override by HOD {current_user.name}"
    
    # Audit log
    audit = AuditLog(
        action_type="MANUAL_EDIT",
        details=f"Manual substitute override for {alloc.class_group.name} on {alloc.date} period {alloc.period_number}: assigned {sub.user.name}.",
        performed_by_id=current_user.id
    )
    db.add(audit)
    db.commit()
    
    return {"status": "SUCCESS", "message": f"Successfully assigned {sub.user.name} for the period."}

@router.get("/swaps/pending")
def get_pending_swaps(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    from app.models.leave import SwapRequest
    query = db.query(SwapRequest).filter(SwapRequest.status == "PENDING_APPROVAL")
    if current_user.role == "HOD":
        query = query.join(Faculty, SwapRequest.sender_faculty_id == Faculty.id).filter(
            Faculty.department_id == current_user.department_id
        )
    swaps = query.all()
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
            "reason": s.reason
        })
    return res

@router.post("/swaps/{swap_id}/action")
def take_swap_action(
    swap_id: int,
    action: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hod)
):
    from app.models.leave import SwapRequest, SubstituteAllocation
    from app.models.schedule import TimetableSlot
    swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")
        
    status_val = action.get("status")
    if status_val not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid action status")
        
    swap.status = status_val
    
    if status_val == "APPROVED":
        # Get original weekly slot A to find class group id
        slot_a = db.query(TimetableSlot).filter(
            TimetableSlot.faculty_id == swap.sender_faculty_id,
            TimetableSlot.day_of_week == swap.date_a.strftime("%A"),
            TimetableSlot.period_number == swap.period_a,
            TimetableSlot.is_temporary == False
        ).first()
        
        if slot_a:
            alloc_a = SubstituteAllocation(
                date=swap.date_a,
                period_number=swap.period_a,
                class_group_id=slot_a.class_group_id,
                original_faculty_id=swap.sender_faculty_id,
                substitute_id=swap.receiver_faculty_id,
                status="RESOLVED",
                explanation=f"Peer-to-peer Hour Swap: {swap.receiver_faculty.user.name} covering for {swap.sender_faculty.user.name}."
            )
            db.add(alloc_a)
            
            # Log individual substitution to AuditLog
            audit_detail = f"Substitution Auto-Allocated (Swap): {swap.receiver_faculty.user.name} covered for {swap.sender_faculty.user.name} on {swap.date_a} (Period {swap.period_a}, Class {slot_a.class_group.name})."
            sub_audit = AuditLog(
                action_type="SUBSTITUTION_ALLOCATE",
                details=audit_detail,
                performed_by_id=None
            )
            db.add(sub_audit)
            
        # Handle slot B swap if date_b is provided
        if swap.date_b and swap.period_b:
            slot_b = db.query(TimetableSlot).filter(
                TimetableSlot.faculty_id == swap.receiver_faculty_id,
                TimetableSlot.day_of_week == swap.date_b.strftime("%A"),
                TimetableSlot.period_number == swap.period_b,
                TimetableSlot.is_temporary == False
            ).first()
            
            if slot_b:
                alloc_b = SubstituteAllocation(
                    date=swap.date_b,
                    period_number=swap.period_b,
                    class_group_id=slot_b.class_group_id,
                    original_faculty_id=swap.receiver_faculty_id,
                    substitute_id=swap.sender_faculty_id,
                    status="RESOLVED",
                    explanation=f"Peer-to-peer Hour Swap: {swap.sender_faculty.user.name} covering for {swap.receiver_faculty.user.name}."
                )
                db.add(alloc_b)
                
                # Log individual substitution to AuditLog
                audit_detail_b = f"Substitution Auto-Allocated (Swap): {swap.sender_faculty.user.name} covered for {swap.receiver_faculty.user.name} on {swap.date_b} (Period {swap.period_b}, Class {slot_b.class_group.name})."
                sub_audit_b = AuditLog(
                    action_type="SUBSTITUTION_ALLOCATE",
                    details=audit_detail_b,
                    performed_by_id=None
                )
                db.add(sub_audit_b)
                
        # Log to AuditLog
        audit = AuditLog(
            action_type="SWAP_APPROVE",
            details=f"Approved Hour Swap: {swap.sender_faculty.user.name} <-> {swap.receiver_faculty.user.name}.",
            performed_by_id=current_user.id
        )
        db.add(audit)
        
    db.commit()
    return {"status": "SUCCESS", "swap_status": swap.status}

@router.get("/swaps/list")
def list_all_swaps(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    from app.models.leave import SwapRequest
    query = db.query(SwapRequest)
    if current_user.role == "HOD":
        query = query.join(Faculty, SwapRequest.sender_faculty_id == Faculty.id).filter(
            Faculty.department_id == current_user.department_id
        )
    swaps = query.order_by(SwapRequest.created_at.desc()).all()
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
            "created_at": s.created_at
        })
    return res

@router.post("/timetable/edit")
def edit_timetable_slot(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hod)
):
    from app.models.schedule import TimetableSlot
    
    # Extract payload manually or via Pydantic model (using dict here for flexibility if not imported)
    class_group_id = payload.get("class_group_id")
    day_of_week = payload.get("day_of_week")
    period_number = payload.get("period_number")
    new_faculty_id = payload.get("new_faculty_id")
    
    slot = db.query(TimetableSlot).filter(
        TimetableSlot.class_group_id == class_group_id,
        TimetableSlot.day_of_week == day_of_week,
        TimetableSlot.period_number == period_number,
        TimetableSlot.is_temporary == False
    ).first()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Base timetable slot not found for this period.")
        
    # Security check: Ensure HOD is editing a slot taught by their department OR for a class in their department
    if current_user.role == "HOD":
        if slot.faculty.department_id != current_user.department_id and slot.class_group.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot edit timetable for other departments.")
            
    new_fac = db.query(Faculty).filter(Faculty.id == new_faculty_id).first()
    if not new_fac:
        raise HTTPException(status_code=404, detail="New faculty not found.")
        
    old_fac_name = slot.faculty.user.name
    slot.faculty_id = new_fac.id
    
    # Audit log
    audit = AuditLog(
        action_type="MANUAL_EDIT",
        details=f"Timetable base edit for Class {slot.class_group.name} on {day_of_week} Period {period_number}: Reassigned from {old_fac_name} to {new_fac.user.name}.",
        performed_by_id=current_user.id
    )
    db.add(audit)
    db.commit()
    
    return {"status": "SUCCESS", "message": "Timetable slot updated successfully."}

from pydantic import BaseModel
from app.models.schedule import TimetableSlot

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
def process_nlp_query(request: QueryRequest, db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    AI Query Assistant Endpoint.
    Uses regex/heuristics to parse natural language queries and return actionable data.
    """
    import re
    query_text = request.query.lower().strip()
    
    # 1. Free / Busy Faculty Query: "who is free/busy on monday period 1"
    time_match = re.search(r'who is (free|available|busy|working|teaching) on (\w+) period (\d+)', query_text)
    if time_match:
        status = time_match.group(1).lower()
        day_str = time_match.group(2).capitalize()
        period_num = int(time_match.group(3))
        
        # Get all faculty in dept
        all_fac = db.query(Faculty).filter(Faculty.department_id == current_user.department_id).all()
        
        # Get faculty teaching on that day/period
        busy_slots = db.query(TimetableSlot).join(Faculty).filter(
            Faculty.department_id == current_user.department_id,
            TimetableSlot.day_of_week == day_str,
            TimetableSlot.period_number == period_num
        ).all()
        
        if status in ['free', 'available']:
            busy_fac_ids = {s.faculty_id for s in busy_slots}
            results = [f.user.name for f in all_fac if f.id not in busy_fac_ids]
            message = f"Found {len(results)} faculty members free on {day_str} Period {period_num}."
        else:
            results = [f"{s.faculty.user.name} (Class {s.class_group.name})" for s in busy_slots]
            message = f"Found {len(results)} faculty members busy teaching on {day_str} Period {period_num}."
            
        return {
            "intent": "time_query",
            "message": message,
            "data": results
        }
        
    # 2. Overload / Burnout Query
    if "overload" in query_text or "burnout" in query_text:
        faculties = db.query(Faculty).filter(Faculty.department_id == current_user.department_id).all()
        overloaded = []
        for f in faculties:
            load_ratio = f.current_workload / max(1, f.max_hours_per_week)
            if load_ratio > 0.8:
                overloaded.append(f"{f.user.name} ({f.current_workload}/{f.max_hours_per_week} hrs)")
                
        if overloaded:
            return {
                "intent": "overload",
                "message": f"Found {len(overloaded)} faculty members operating near or over capacity.",
                "data": overloaded
            }
        else:
            return {
                "intent": "overload",
                "message": "All faculty members are currently within safe workload bounds.",
                "data": []
            }
            
    # 3. Subject Query: "who teaches machine learning"
    subject_match = re.search(r'who teaches (.*)', query_text)
    if subject_match:
        subject_name = subject_match.group(1).strip().replace("?", "")
        subject = db.query(Subject).filter(
            Subject.department_id == current_user.department_id,
            Subject.name.ilike(f"%{subject_name}%")
        ).first()
        
        if subject:
            qualified = [f.user.name for f in subject.qualified_faculties]
            return {
                "intent": "subject_teachers",
                "message": f"Faculty qualified to teach '{subject.name}':",
                "data": qualified
            }
        else:
            return {
                "intent": "subject_teachers",
                "message": f"Could not find a subject matching '{subject_name}' in your department.",
                "data": []
            }

    # 4. Teacher Schedule Query: "where is dr. smith on monday?"
    teacher_match = re.search(r'where is (.*?) on (\w+)', query_text)
    if teacher_match:
        teacher_name = teacher_match.group(1).strip()
        day_str = teacher_match.group(2).capitalize()
        
        faculty = db.query(Faculty).join(User).filter(
            Faculty.department_id == current_user.department_id,
            User.name.ilike(f"%{teacher_name}%")
        ).first()
        
        if faculty:
            slots = db.query(TimetableSlot).filter(
                TimetableSlot.faculty_id == faculty.id,
                TimetableSlot.day_of_week == day_str
            ).order_by(TimetableSlot.period_number).all()
            
            schedule = [f"Period {s.period_number}: Class {s.class_group.name} ({s.subject.name}) in Room {s.classroom.name}" for s in slots]
            
            return {
                "intent": "teacher_schedule",
                "message": f"Schedule for {faculty.user.name} on {day_str}:" if schedule else f"{faculty.user.name} has no classes scheduled on {day_str}.",
                "data": schedule
            }
        else:
            return {
                "intent": "teacher_schedule",
                "message": f"Could not find a faculty member matching '{teacher_name}'.",
                "data": []
            }
            
    # Default Fallback
    return {
        "intent": "unknown",
        "message": "I didn't quite understand that. Try asking:\n- Who is free on Monday period 1?\n- Who is overloaded?\n- Who teaches Data Science?\n- Where is Santhi on Tuesday?",
        "data": []
    }
