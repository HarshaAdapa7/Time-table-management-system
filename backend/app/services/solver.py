import logging
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy.orm import Session
from ortools.sat.python import cp_model

from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup, TimetableSlot
from app.models.leave import LeaveRequest, SubstituteAllocation, SwapRequest, AuditLog
from app.services.recommender import score_substitute_candidates
from app.utils.explainability import explain_substitution_conflict

logger = logging.getLogger("scheduler")


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = list(range(1, 7))  # 6 periods per day for hackathon demo simplicity (e.g., 9 AM to 3 PM)

def generate_base_timetable(db: Session, department_id: int | None = None) -> dict:
    """
    Generates a complete school timetable from scratch using OR-Tools CP-SAT.
    """
    # 1. Fetch data from DB
    query_faculties = db.query(Faculty)
    query_subjects = db.query(Subject)
    query_classes = db.query(ClassGroup)
    query_classrooms = db.query(Classroom)
    
    if department_id:
        query_faculties = query_faculties.filter(Faculty.department_id == department_id)
        query_subjects = query_subjects.filter(Subject.department_id == department_id)
        query_classes = query_classes.filter(ClassGroup.department_id == department_id)
        
    faculties = query_faculties.all()
    subjects = query_subjects.all()
    class_groups = query_classes.all()
    classrooms = query_classrooms.all()
    
    if not faculties or not subjects or not class_groups or not classrooms:
        return {"status": "FAILED", "reason": "Insufficient data to generate timetable. Ensure Faculty, Subjects, Classes, and Rooms are uploaded."}
        
    # Mapping helper lookups
    fac_map = {f.id: f for f in faculties}
    sub_map = {s.id: s for s in subjects}
    class_map = {c.id: c for c in class_groups}
    room_map = {r.id: r for r in classrooms}
    
    # 2. Build the CP-SAT Model
    model = cp_model.CpModel()
    
    # Map class groups to specific classrooms to optimize search space and avoid combinatorial explosion
    class_room_map = {}
    for i, c in enumerate(class_groups):
        room_idx = i % len(classrooms)
        class_room_map[c.id] = classrooms[room_idx].id

    # Variables: X[day, period, class, faculty, subject, room] = Boolean
    # To reduce variable size, we filter eligible combinations
    variables = {}
    
    # Pre-map qualified faculties per subject
    qualified_facs_for_subject = defaultdict(list)
    for f in faculties:
        for s in f.qualified_subjects:
            qualified_facs_for_subject[s.id].append(f.id)
            
    # Pre-map subjects each class needs (for base demo, each class has a set of subjects they must learn)
    # If the database doesn't explicitly store class-subject requirements, we assume all subjects in the department can be taught.
    # We will assume each subject requires a certain number of hours per week for each class group.
    
    for d in DAYS:
        for p in PERIODS:
            for c in class_groups:
                r_id = class_room_map.get(c.id)
                if not r_id:
                    continue
                for s in subjects:
                    # Only create variables if class and subject belong to the same department
                    if c.department_id != s.department_id:
                        continue
                    
                    # Only create variables for faculties qualified for this subject
                    eligible_facs = qualified_facs_for_subject[s.id]
                    for f_id in eligible_facs:
                        var_name = f"x_{d}_{p}_{c.id}_{f_id}_{s.id}_{r_id}"
                        variables[(d, p, c.id, f_id, s.id, r_id)] = model.NewBoolVar(var_name)
                            
    # --- HARD CONSTRAINTS ---
    
    # Constraint 1: A class can have at most one slot (teacher, subject, room) per period
    for d in DAYS:
        for p in PERIODS:
            for c in class_groups:
                slots_for_class = [
                    variables[key] for key in variables 
                    if key[0] == d and key[1] == p and key[2] == c.id
                ]
                model.AddAtMostOne(slots_for_class)
                
    # Constraint 2: A faculty can teach at most one class at a time
    for d in DAYS:
        for p in PERIODS:
            for f in faculties:
                slots_for_faculty = [
                    variables[key] for key in variables 
                    if key[0] == d and key[1] == p and key[3] == f.id
                ]
                model.AddAtMostOne(slots_for_faculty)
                
    # Constraint 3: A classroom can host at most one class at a time
    for d in DAYS:
        for p in PERIODS:
            for r in classrooms:
                slots_for_room = [
                    variables[key] for key in variables 
                    if key[0] == d and key[1] == p and key[5] == r.id
                ]
                model.AddAtMostOne(slots_for_room)
                
    # Constraint 4: Subject-hours-per-week satisfied for each ClassGroup
    # Sum over all days and periods of slots for (class, subject) must equal hours_required_per_week
    for c in class_groups:
        for s in subjects:
            # Skip if class and subject are in different departments
            if c.department_id != s.department_id:
                continue
                
            slots_for_class_subject = [
                variables[key] for key in variables
                if key[2] == c.id and key[4] == s.id
            ]
            # If no slots are available, we can't satisfy it (should only happen if no qualified teachers)
            if slots_for_class_subject:
                # Add exact equality constraint
                model.Add(sum(slots_for_class_subject) == s.hours_required_per_week)
                
    # Constraint 5: Faculty maximum workload limit per week
    for f in faculties:
        slots_for_faculty_all = [
            variables[key] for key in variables
            if key[3] == f.id
        ]
        if slots_for_faculty_all:
            model.Add(sum(slots_for_faculty_all) <= f.max_hours_per_week)
            
    # --- SOFT CONSTRAINTS / OBJECTIVES ---
    # Objective: Minimize faculty load variance and back-to-back load
    # Let's minimize the sum of consecutive teaching periods for faculty
    consecutive_penalties = []
    for f in faculties:
        for d in DAYS:
            # Check for 3 consecutive periods: (p, p+1, p+2)
            for idx in range(len(PERIODS) - 2):
                p1, p2, p3 = PERIODS[idx], PERIODS[idx+1], PERIODS[idx+2]
                
                # Active flags
                f_p1 = model.NewBoolVar(f"act_{f.id}_{d}_{p1}")
                f_p2 = model.NewBoolVar(f"act_{f.id}_{d}_{p2}")
                f_p3 = model.NewBoolVar(f"act_{f.id}_{d}_{p3}")
                
                # Connect active flags to vars
                vars_p1 = [variables[k] for k in variables if k[0] == d and k[1] == p1 and k[3] == f.id]
                vars_p2 = [variables[k] for k in variables if k[0] == d and k[1] == p2 and k[3] == f.id]
                vars_p3 = [variables[k] for k in variables if k[0] == d and k[1] == p3 and k[3] == f.id]
                
                model.Add(f_p1 == sum(vars_p1))
                model.Add(f_p2 == sum(vars_p2))
                model.Add(f_p3 == sum(vars_p3))
                
                # Penalty variable if all three are active
                triple_active = model.NewBoolVar(f"triple_{f.id}_{d}_{p1}")
                model.AddBoolAnd([f_p1, f_p2, f_p3]).OnlyEnforceIf(triple_active)
                model.AddBoolOr([f_p1.Not(), f_p2.Not(), f_p3.Not()]).OnlyEnforceIf(triple_active.Not())
                
                consecutive_penalties.append(triple_active)

    # Minimize penalties
    model.Minimize(sum(consecutive_penalties))
    
    # 3. Solve the Model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0 # Set time limit
    status = solver.Solve(model)
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Delete old timetable slots
        if department_id:
            # Scope deletion to department
            db.query(TimetableSlot).filter(
                TimetableSlot.class_group_id.in_([c.id for c in class_groups])
            ).delete(synchronize_session=False)
        else:
            db.query(TimetableSlot).delete(synchronize_session=False)
            
        db.commit()
        
        # Save generated timetable
        slots_created = 0
        faculty_hours = defaultdict(float)
        
        for key, var in variables.items():
            if solver.Value(var) == 1:
                day, period, c_id, f_id, s_id, r_id = key
                slot = TimetableSlot(
                    day_of_week=day,
                    period_number=period,
                    class_group_id=c_id,
                    faculty_id=f_id,
                    subject_id=s_id,
                    classroom_id=r_id,
                    is_temporary=False
                )
                db.add(slot)
                faculty_hours[f_id] += 1.0
                slots_created += 1
                
        # Update current workload workloads
        for f_id, hrs in faculty_hours.items():
            fac = fac_map.get(f_id)
            if fac:
                fac.current_workload = hrs
                
        db.commit()
        
        # Log Audit Trail
        audit = AuditLog(
            action_type="BASE_GENERATION",
            details=f"Generated base timetable with {slots_created} slots.",
            performed_by_id=None # System generated
        )
        db.add(audit)
        db.commit()
        
        return {"status": "SUCCESS", "slots_created": slots_created}
    else:
        # Infeasibility diagnostics
        conflict_report = explain_base_conflicts(db, class_groups, subjects, faculties)
        return {
            "status": "FAILED", 
            "reason": "Solver failed to find a valid layout satisfying all constraints.", 
            "conflicts": conflict_report
        }

def explain_base_conflicts(db: Session, classes, subjects, faculties) -> list[str]:
    """
    Checks for obvious bottleneck issues when the solver fails.
    """
    conflicts = []
    
    # 1. Check if any subject has zero qualified faculty
    for sub in subjects:
        qualified = db.query(Faculty).filter(Faculty.qualified_subjects.contains(sub)).count()
        if qualified == 0:
            conflicts.append(f"Subject '{sub.name}' ({sub.code}) has no qualified faculty assigned to teach it.")
            
    # 2. Check total hours required vs capacity
    total_required_hours = sum(c.hours_required_per_week for c in subjects) * len(classes)
    total_capacity_hours = sum(f.max_hours_per_week for f in faculties)
    if total_required_hours > total_capacity_hours:
        conflicts.append(f"Total required subject hours ({total_required_hours} hrs/week) exceeds total faculty capacity ({total_capacity_hours} hrs/week).")
        
    if not conflicts:
        conflicts.append("No obvious bottlenecks. The schedule might be over-constrained due to availability conflicts or room limitations.")
        
    return conflicts


def resolve_leave_substitutions(db: Session, leave_request_id: int) -> dict:
    """
    Incremental Re-optimization Layer.
    Only repairs slots affected by an approved leave request on a specific date range.
    """
    leave_req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
    if not leave_req:
        return {"status": "FAILED", "reason": "Leave request not found."}
        
    # Get absent faculty
    absent_faculty = db.query(Faculty).filter(Faculty.id == leave_req.faculty_id).first()
    
    # Determine affected dates
    # For simplicity, we loop through dates and solve daily
    import datetime as dt
    start_date = leave_req.start_date
    end_date = leave_req.end_date
    
    current_date = start_date
    slots_processed = 0
    slots_resolved = 0
    allocations_details = []
    
    while current_date <= end_date:
        # Get day of week string
        day_str = current_date.strftime("%A")
        
        if day_str not in DAYS:
            current_date += dt.timedelta(days=1)
            continue
            
        # Find regular slots for this faculty on this day
        query_slots = db.query(TimetableSlot).filter(
            TimetableSlot.day_of_week == day_str,
            TimetableSlot.faculty_id == absent_faculty.id,
            TimetableSlot.is_temporary == False
        )
        
        # If partial leave, filter by specific periods
        if leave_req.specific_periods:
            periods = [int(p.strip()) for p in leave_req.specific_periods.split(",") if p.strip()]
            query_slots = query_slots.filter(TimetableSlot.period_number.in_(periods))
            
        affected_slots = query_slots.all()
        
        for slot in affected_slots:
            slots_processed += 1
            
            # Find candidate substitutes for this specific slot
            # Rule: same-subject expertise > free slot match > current workload
            candidates = score_substitute_candidates(db, slot.subject_id, day_str, slot.period_number, current_date)
            
            substitute_id = None
            status = "UNRESOLVED"
            
            if candidates:
                # Pick the highest scoring candidate
                best_cand = candidates[0]
                substitute_id = best_cand["faculty_id"]
                status = "RESOLVED"
                explanation = f"Auto-allocated: {best_cand['name']} (Score: {best_cand['score']:.1f}) - {best_cand['reason']}"
                slots_resolved += 1
            else:
                explanation = explain_substitution_conflict(db, slot.subject_id, day_str, slot.period_number, current_date)
            
            # Create SubstituteAllocation
            alloc = SubstituteAllocation(
                leave_request_id=leave_req.id,
                date=current_date,
                period_number=slot.period_number,
                class_group_id=slot.class_group_id,
                original_faculty_id=absent_faculty.id,
                substitute_id=substitute_id,
                status=status,
                explanation=explanation
            )
            db.add(alloc)
            
            # Log individual substitution to AuditLog
            sub_name = best_cand["name"] if substitute_id else "None"
            audit_detail = f"Substitution Auto-Allocated: {sub_name} covered for {absent_faculty.user.name} on {current_date} (Period {slot.period_number}, Class {slot.class_group.name})."
            sub_audit = AuditLog(
                action_type="SUBSTITUTION_ALLOCATE",
                details=audit_detail,
                performed_by_id=None # System auto-allocated
            )
            db.add(sub_audit)
            
            allocations_details.append({
                "date": current_date.isoformat(),
                "period": slot.period_number,
                "class_group": slot.class_group.name,
                "substitute": sub_name,
                "status": status,
                "reason": explanation
            })
            
        current_date += dt.timedelta(days=1)
        
    db.commit()
    
    # Audit Log
    if slots_processed == 0:
        details = f"Approved leave for {absent_faculty.user.name} from {start_date} to {end_date}. No classes were scheduled for them on these dates, so no substitutes were needed."
    else:
        details = f"Approved leave for {absent_faculty.user.name} from {start_date} to {end_date}. Resolved {slots_resolved}/{slots_processed} slots."
        
    audit = AuditLog(
        action_type="LEAVE_APPROVE",
        details=details,
        performed_by_id=leave_req.approved_by_id
    )
    db.add(audit)
    db.commit()
    
    return {
        "status": "SUCCESS" if slots_resolved == slots_processed else "PARTIAL",
        "total_slots": slots_processed,
        "resolved_slots": slots_resolved,
        "allocations": allocations_details
    }
