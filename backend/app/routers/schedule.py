from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.database import get_db
from app.auth.dependencies import get_current_user, require_any_user
from app.models.user import User
from app.models.schedule import ClassGroup, Faculty, TimetableSlot, Classroom, Subject
from app.models.leave import SubstituteAllocation
from app.schemas.schedule import TimetableSlotResponse
from app.schemas.leave import SubstituteAllocationResponse

router = APIRouter(prefix="/api/schedule", tags=["Schedule Query"])

def build_slot_response(db: Session, slot: TimetableSlot, target_date: date | None = None) -> dict:
    # Check if there is an active approved substitute allocation for this slot on target_date
    substitute_name = None
    is_subbed = False
    
    if target_date:
        alloc = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.original_faculty_id == slot.faculty_id,
            SubstituteAllocation.date == target_date,
            SubstituteAllocation.period_number == slot.period_number,
            SubstituteAllocation.status == "RESOLVED"
        ).first()
        
        if alloc and alloc.substitute:
            substitute_name = alloc.substitute.user.name
            is_subbed = True
            
    faculty_name = substitute_name if is_subbed else slot.faculty.user.name
    
    return {
        "id": slot.id,
        "day_of_week": slot.day_of_week,
        "period_number": slot.period_number,
        "subject_code": slot.subject.code,
        "subject_name": slot.subject.name,
        "faculty_name": faculty_name + (" (Substitute)" if is_subbed else ""),
        "classroom_name": slot.classroom.name if slot.classroom else None,
        "classroom_number": slot.classroom.room_number if slot.classroom else None,
        "class_group_name": slot.class_group.name,
        "is_temporary": slot.is_temporary,
        "effective_date": slot.effective_date,
        "is_substitution": is_subbed
    }

@router.get("/class/{class_id}", response_model=List[TimetableSlotResponse])
def get_class_timetable(
    class_id: int, 
    target_date: Optional[date] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user)
):
    """
    Returns the timetable for a specific class. If target_date is provided, 
    it applies active substitutions for that day.
    """
    class_group = db.query(ClassGroup).filter(ClassGroup.id == class_id).first()
    if not class_group:
        raise HTTPException(status_code=404, detail="Class Group not found")
        
    day_str = target_date.strftime("%A") if target_date else None
    
    # Query normal weekly timetable slots
    query = db.query(TimetableSlot).filter(
        TimetableSlot.class_group_id == class_id,
        TimetableSlot.is_temporary == False
    )
    if day_str:
        query = query.filter(TimetableSlot.day_of_week == day_str)
        
    slots = query.all()
    
    return [build_slot_response(db, slot, target_date) for slot in slots]

@router.get("/faculty/{faculty_id}", response_model=List[TimetableSlotResponse])
def get_faculty_timetable(
    faculty_id: int,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user)
):
    """
    Returns the timetable for a specific faculty. If target_date is provided,
    it accounts for their leaves and substitution obligations.
    """
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    day_str = target_date.strftime("%A") if target_date else None
    
    # Check if faculty is on leave for the target_date
    # If on leave, their regular slots will be covered by substitutes (or show as vacant)
    # Also, this faculty might be substituting for someone else on this date!
    
    # Fetch regular weekly slots
    query = db.query(TimetableSlot).filter(
        TimetableSlot.faculty_id == faculty_id,
        TimetableSlot.is_temporary == False
    )
    if day_str:
        query = query.filter(TimetableSlot.day_of_week == day_str)
        
    regular_slots = query.all()
    
    response_slots = []
    
    # For each regular slot, check if they are absent on target_date
    for slot in regular_slots:
        if target_date:
            # Check leave status
            # If on leave, don't show it under their active teaching list for today (or flag as covered)
            is_absent = db.query(SubstituteAllocation).filter(
                SubstituteAllocation.original_faculty_id == faculty_id,
                SubstituteAllocation.date == target_date,
                SubstituteAllocation.period_number == slot.period_number
            ).first()
            if is_absent:
                # Faculty is not teaching this. Skip it or represent it differently.
                continue
        response_slots.append(build_slot_response(db, slot, target_date))
        
    # If target_date is provided, add slots where this faculty is acting as a substitute!
    if target_date:
        sub_allocs = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.substitute_id == faculty_id,
            SubstituteAllocation.date == target_date,
            SubstituteAllocation.status == "RESOLVED"
        ).all()
        
        for alloc in sub_allocs:
            # Find the original timetable slot to fetch details
            orig_slot = db.query(TimetableSlot).filter(
                TimetableSlot.day_of_week == day_str,
                TimetableSlot.period_number == alloc.period_number,
                TimetableSlot.class_group_id == alloc.class_group_id,
                TimetableSlot.is_temporary == False
            ).first()
            
            if orig_slot:
                # Build slot response with substitute name
                res = build_slot_response(db, orig_slot, target_date)
                res["faculty_name"] = f"{faculty.user.name} (Substitute for {orig_slot.faculty.user.name})"
                response_slots.append(res)
                
    return response_slots

@router.get("/classes", response_model=List[dict])
def list_classes(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    classes = db.query(ClassGroup).all()
    return [{"id": c.id, "name": c.name, "department_name": c.department.name if c.department else "None"} for c in classes]

@router.get("/faculties", response_model=List[dict])
def list_faculties(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    faculties = db.query(Faculty).all()
    res = []
    for f in faculties:
        classes_assigned = db.query(ClassGroup.name).join(TimetableSlot).filter(
            TimetableSlot.faculty_id == f.id
        ).distinct().all()
        class_names = [c[0] for c in classes_assigned]
        assigned_classes_str = ", ".join(class_names) if class_names else "No Classes"
        
        res.append({
            "id": f.id, 
            "name": f.user.name, 
            "email": f.user.email,
            "department_name": f.department.name if f.department else "None",
            "assigned_classes": assigned_classes_str
        })
    return res

@router.get("/conflicts", response_model=List[SubstituteAllocationResponse])
def get_timetable_conflicts(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    """
    Returns all unresolved substitute allocations (periods that have no teacher cover).
    """
    unresolved = db.query(SubstituteAllocation).filter(
        SubstituteAllocation.status == "UNRESOLVED"
    ).all()
    return unresolved

@router.get("/classrooms", response_model=List[dict])
def list_classrooms(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    classrooms = db.query(Classroom).all()
    return [{"id": r.id, "name": r.name, "room_number": r.room_number, "capacity": r.capacity} for r in classrooms]

@router.get("/subjects", response_model=List[dict])
def list_subjects(db: Session = Depends(get_db), current_user: User = Depends(require_any_user)):
    subjects = db.query(Subject).all()
    return [{"id": s.id, "code": s.code, "name": s.name, "hours_required": s.hours_required_per_week} for s in subjects]
