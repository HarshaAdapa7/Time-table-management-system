from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Body
from sqlalchemy.orm import Session
import traceback
import logging

logger = logging.getLogger("app")
from typing import List, Optional

from app.database import get_db
from app.auth.dependencies import require_admin, require_hod
from app.models.user import User
from app.models.schedule import Faculty, Subject, ClassGroup, Classroom, TimetableSlot
from app.models.leave import AuditLog
from app.utils.csv_loader import load_classroom_csv, load_subjects_csv, load_classes_csv, load_faculty_csv
from app.services.solver import generate_base_timetable

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

@router.post("/upload/classrooms")
async def upload_classrooms(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        content = await file.read()
        csv_data = content.decode("utf-8")
        imported = load_classroom_csv(db, csv_data)
        return {"status": "SUCCESS", "message": f"Successfully imported/updated {imported} classrooms."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

@router.post("/upload/subjects")
async def upload_subjects(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        content = await file.read()
        csv_data = content.decode("utf-8")
        imported = load_subjects_csv(db, csv_data)
        return {"status": "SUCCESS", "message": f"Successfully imported/updated {imported} subjects."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

@router.post("/upload/classes")
async def upload_classes(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        content = await file.read()
        csv_data = content.decode("utf-8")
        imported = load_classes_csv(db, csv_data)
        return {"status": "SUCCESS", "message": f"Successfully imported/updated {imported} classes."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

@router.post("/upload/faculty")
async def upload_faculty(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        content = await file.read()
        csv_data = content.decode("utf-8")
        imported = load_faculty_csv(db, csv_data)
        return {"status": "SUCCESS", "message": f"Successfully imported/updated {imported} faculty."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

@router.post("/generate-base")
def trigger_base_generation(
    payload: Optional[dict] = Body(None),
    department_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    logger.info(f"generate-base endpoint hit. department_id: {department_id}, payload: {payload}")
    try:
        result = generate_base_timetable(db, department_id)
        if result["status"] == "FAILED":
            logger.warning(f"generate-base solver execution failed: {result}")
            raise HTTPException(status_code=422, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"generate-base failed with exception: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/workload")
def get_workload_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hod) # Allow HODs and Admins
):
    """
    Returns faculty workloads and their burnout risk scores.
    """
    faculties = db.query(Faculty).all()
    report = []
    for f in faculties:
        report.append({
            "faculty_id": f.id,
            "name": f.user.name,
            "email": f.user.email,
            "department": f.department.name if f.department else "None",
            "max_hours": f.max_hours_per_week,
            "current_hours": f.current_workload,
            "burnout_risk": f.burnout_risk_score
        })
    return report

@router.get("/reports/audit-logs", response_model=List[dict])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hod) # Allow HODs and Admins
):
    query = db.query(AuditLog)
    
    # Hide edited logs (MANUAL_EDIT) from admin
    if current_user.role == "ADMIN":
        query = query.filter(AuditLog.action_type != "MANUAL_EDIT")
        
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    
    return [{
        "id": l.id,
        "action_type": l.action_type,
        "details": l.details,
        "performer_name": l.actor.name if l.actor else "System",
        "timestamp": l.timestamp.isoformat()
    } for l in logs]

@router.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):
    facs = db.query(Faculty).all()
    res = []
    for f in facs:
        res.append({
            "faculty_name": f.user.name if f.user else "Unknown",
            "department_id": f.department_id,
            "qualified_subjects": [s.code for s in f.qualified_subjects]
        })
    return {
        "faculties": res,
        "classrooms": [{"id": r.id, "num": r.room_number} for r in db.query(Classroom).all()],
        "subjects": [{"id": s.id, "code": s.code, "department_id": s.department_id} for s in db.query(Subject).all()],
        "classes": [{"id": c.id, "name": c.name, "department_id": c.department_id} for c in db.query(ClassGroup).all()]
    }

@router.get("/run-test")
def run_test(db: Session = Depends(get_db)):
    from ortools.sat.python import cp_model
    from collections import defaultdict
    
    faculties = db.query(Faculty).all()
    subjects = db.query(Subject).all()
    class_groups = db.query(ClassGroup).all()
    classrooms = db.query(Classroom).all()
    
    model = cp_model.CpModel()
    
    class_room_map = {}
    for i, c in enumerate(class_groups):
        room_idx = i % len(classrooms)
        class_room_map[c.id] = classrooms[room_idx].id
        
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    PERIODS = list(range(1, 7))
    
    variables = {}
    qualified_facs_for_subject = defaultdict(list)
    for f in faculties:
        for s in f.qualified_subjects:
            qualified_facs_for_subject[s.id].append(f.id)
            
    for d in DAYS:
        for p in PERIODS:
            for c in class_groups:
                r_id = class_room_map.get(c.id)
                if not r_id:
                    continue
                for s in subjects:
                    if c.department_id != s.department_id:
                        continue
                    eligible_facs = qualified_facs_for_subject[s.id]
                    for f_id in eligible_facs:
                        key = (d, p, c.id, f_id, s.id, r_id)
                        var_name = f"x_{d}_{p}_{c.id}_{f_id}_{s.id}_{r_id}"
                        variables[key] = model.NewBoolVar(var_name)
                        
    # Constraint checks: list class-subject requirements that have NO variables
    unmapped = []
    for c in class_groups:
        for s in subjects:
            if c.department_id != s.department_id:
                continue
            slots_for_class_subject = [
                variables[key] for key in variables
                if key[2] == c.id and key[4] == s.id
            ]
            if not slots_for_class_subject:
                unmapped.append(f"Class: {c.name}, Subject: {s.code} has 0 variables!")
                
    # Add Constraints
    for d in DAYS:
        for p in PERIODS:
            for c in class_groups:
                slots_for_class = [variables[key] for key in variables if key[0] == d and key[1] == p and key[2] == c.id]
                model.AddAtMostOne(slots_for_class)
                
    for d in DAYS:
        for p in PERIODS:
            for f in faculties:
                slots_for_faculty = [variables[key] for key in variables if key[0] == d and key[1] == p and key[3] == f.id]
                model.AddAtMostOne(slots_for_faculty)
                
    for d in DAYS:
        for p in PERIODS:
            for r in classrooms:
                slots_for_room = [variables[key] for key in variables if key[0] == d and key[1] == p and key[5] == r.id]
                model.AddAtMostOne(slots_for_room)
                
    for c in class_groups:
        for s in subjects:
            if c.department_id != s.department_id:
                continue
            slots_for_class_subject = [variables[key] for key in variables if key[2] == c.id and key[4] == s.id]
            if slots_for_class_subject:
                model.Add(sum(slots_for_class_subject) == s.hours_required_per_week)
                
    for f in faculties:
        slots_for_faculty_all = [variables[key] for key in variables if key[3] == f.id]
        if slots_for_faculty_all:
            model.Add(sum(slots_for_faculty_all) <= f.max_hours_per_week)
            
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    
    status_name = "UNKNOWN"
    if status == cp_model.OPTIMAL:
        status_name = "OPTIMAL"
    elif status == cp_model.FEASIBLE:
        status_name = "FEASIBLE"
    elif status == cp_model.INFEASIBLE:
        status_name = "INFEASIBLE"
        
    class_map = {c.id: c.name for c in class_groups}
    room_map = {r.id: r.name for r in classrooms}
    class_room_names = {class_map[c_id]: room_map[r_id] for c_id, r_id in class_room_map.items() if c_id in class_map and r_id in room_map}
    
    return {
        "status": status_name,
        "num_variables": len(variables),
        "unmapped_requirements": unmapped,
        "class_room_map": class_room_names,
    }
