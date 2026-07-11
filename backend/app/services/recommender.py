from sqlalchemy.orm import Session
from datetime import date
from app.models.schedule import Faculty, Subject, TimetableSlot
from app.models.leave import LeaveRequest, SubstituteAllocation
from app.services.ml_predictor import predict_burnout_risk

def score_substitute_candidates(
    db: Session, 
    subject_id: int, 
    day_str: str, 
    period_number: int, 
    target_date: date
) -> list[dict]:
    """
    Ranks substitute candidates using a composite scoring function:
    same-subject expertise > free slot match > current workload > department proximity > ML burnout risk.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return []
        
    # Get all faculty qualified to teach this subject
    qualified_faculties = db.query(Faculty).join(Faculty.qualified_subjects).filter(Subject.id == subject_id).all()
    
    candidates = []
    
    for faculty in qualified_faculties:
        # Check 1: Is this faculty on leave on target_date, period_number?
        on_leave = db.query(LeaveRequest).filter(
            LeaveRequest.faculty_id == faculty.id,
            LeaveRequest.start_date <= target_date,
            LeaveRequest.end_date >= target_date,
            LeaveRequest.status == "APPROVED"
        ).first()
        
        if on_leave:
            # If full leave, skip. If partial, check if period is listed
            if not on_leave.specific_periods:
                continue # Full day leave
            periods_absent = [int(p.strip()) for p in on_leave.specific_periods.split(",") if p.strip()]
            if period_number in periods_absent:
                continue
                
        # Check 2: Is this faculty already teaching their own class in the base timetable?
        is_teaching = db.query(TimetableSlot).filter(
            TimetableSlot.faculty_id == faculty.id,
            TimetableSlot.day_of_week == day_str,
            TimetableSlot.period_number == period_number,
            TimetableSlot.is_temporary == False
        ).first()
        
        if is_teaching:
            continue
            
        # Check 3: Is this faculty already assigned to substitute cover another slot on this day/period?
        is_substituting = db.query(SubstituteAllocation).filter(
            SubstituteAllocation.substitute_id == faculty.id,
            SubstituteAllocation.date == target_date,
            SubstituteAllocation.period_number == period_number,
            SubstituteAllocation.status == "RESOLVED"
        ).first()
        
        if is_substituting:
            continue

        # Candidate is free! Let's score them
        base_score = 100.0
        reasons = []
        
        # Dept proximity: same department adds a bonus
        same_dept = faculty.department_id == subject.department_id
        if same_dept:
            base_score += 20.0
            reasons.append("Same department")
        else:
            reasons.append("Cross-department")
            
        # Workload utilization: prefer faculty with low load ratio (current / max)
        load_ratio = faculty.current_workload / max(1, faculty.max_hours_per_week)
        # Deduct up to 30 points for high workloads
        workload_deduction = load_ratio * 30.0
        base_score -= workload_deduction
        reasons.append(f"Workload: {faculty.current_workload}/{faculty.max_hours_per_week}h")
        
        # ML Burnout Risk: predict burnout risk score and deduct points
        burnout_risk = predict_burnout_risk(faculty, db)
        burnout_deduction = burnout_risk * 40.0
        base_score -= burnout_deduction
        
        if burnout_risk > 0.6:
            reasons.append(f"Burnout risk alert ({int(burnout_risk*100)}%)")
        else:
            reasons.append(f"Low burnout risk ({int(burnout_risk*100)}%)")
            
        candidates.append({
            "faculty_id": faculty.id,
            "name": faculty.user.name,
            "email": faculty.user.email,
            "department": faculty.department.name if faculty.department else "None",
            "score": base_score,
            "burnout_risk": burnout_risk,
            "reason": ", ".join(reasons)
        })
        
    # Sort candidates by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates
