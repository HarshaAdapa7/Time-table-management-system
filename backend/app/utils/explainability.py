from sqlalchemy.orm import Session
from datetime import date
from app.models.schedule import Faculty, Subject, TimetableSlot
from app.models.leave import LeaveRequest, SubstituteAllocation

def explain_substitution_conflict(
    db: Session, 
    subject_id: int, 
    day_str: str, 
    period_number: int, 
    target_date: date
) -> str:
    """
    Generates a detailed, human-readable reason of why a substitute allocation failed for a slot.
    Scan and logs exact conflict status of each potentially qualified faculty.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return "Subject not found."
        
    # Get all faculty qualified for this subject
    qualified_faculties = db.query(Faculty).join(Faculty.qualified_subjects).filter(Subject.id == subject_id).all()
    
    if not qualified_faculties:
        return f"No faculty members are qualified to teach '{subject.name}' ({subject.code}). Please assign qualified subjects to faculty."
        
    explanations = []
    
    for faculty in qualified_faculties:
        # Check leave status
        leave = db.query(LeaveRequest).filter(
            LeaveRequest.faculty_id == faculty.id,
            LeaveRequest.start_date <= target_date,
            LeaveRequest.end_date >= target_date,
            LeaveRequest.status == "APPROVED"
        ).first()
        
        if leave:
            # Check if full day or partial
            if not leave.specific_periods:
                explanations.append(f"{faculty.user.name}: On approved leave all day ({leave.reason or 'No reason provided'}).")
                continue
            periods_absent = [int(p.strip()) for p in leave.specific_periods.split(",") if p.strip()]
            if period_number in periods_absent:
                explanations.append(f"{faculty.user.name}: On approved leave for Period {period_number} ({leave.reason or 'No reason provided'}).")
                continue
                
        # Check regular teaching slot
        teaching_slot = db.query(TimetableSlot).filter(
            TimetableSlot.faculty_id == faculty.id,
            TimetableSlot.day_of_week == day_str,
            TimetableSlot.period_number == period_number,
            TimetableSlot.is_temporary == False
        ).first()
        
        if teaching_slot:
            explanations.append(f"{faculty.user.name}: Already teaching '{teaching_slot.subject.name}' to Class {teaching_slot.class_group.name} in room {teaching_slot.classroom.room_number if teaching_slot.classroom else 'N/A'}.")
            continue
            
        # Check if already substituting elsewhere
        sub_alloc = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.substitute_id == faculty.id,
            SubstituteAllocation.date == target_date,
            SubstituteAllocation.period_number == period_number,
            SubstituteAllocation.status == "RESOLVED"
        ).first()
        
        if sub_alloc:
            explanations.append(f"{faculty.user.name}: Already assigned as substitute for {sub_alloc.original_faculty.user.name}'s class ({sub_alloc.class_group.name}).")
            continue
            
        # If they are free but weren't picked (should only happen if they were bypassed or if this is called when there ARE candidates)
        explanations.append(f"{faculty.user.name}: Available (Workload: {faculty.current_workload} hrs).")

    # Combine explanations
    header = f"Conflict details for Period {period_number} ({subject.name}):"
    body = "\n".join([f" - {exp}" for exp in explanations])
    return f"{header}\n{body}"
