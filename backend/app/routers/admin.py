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
