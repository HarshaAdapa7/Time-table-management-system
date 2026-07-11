from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, date, timedelta

from app.database import get_db
from app.auth.dependencies import require_hod
from app.models.user import User
from app.models.schedule import Faculty, Department, TimetableSlot, ClassGroup, Classroom, Subject
from app.models.leave import LeaveRequest, SubstituteAllocation, AuditLog, SwapRequest

router = APIRouter(prefix="/api/hod/reports", tags=["HOD Reports"], dependencies=[Depends(require_hod)])

@router.get("/workload")
def get_workload_report(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns faculty workload data including overload alerts.
    """
    faculties = db.query(Faculty).filter(Faculty.department_id == current_user.department_id).all()
    
    workload_data = []
    total_department_hours = 0
    total_capacity = 0
    overloaded_faculty = []
    
    for f in faculties:
        load = f.current_workload
        max_load = f.max_hours_per_week
        total_department_hours += load
        total_capacity += max_load
        
        ratio = load / max(1, max_load)
        is_overloaded = ratio > 0.8
        
        fac_data = {
            "faculty_id": f.id,
            "name": f.user.name,
            "current_workload": load,
            "max_hours": max_load,
            "ratio": ratio,
            "is_overloaded": is_overloaded,
            "burnout_score": f.burnout_risk_score
        }
        workload_data.append(fac_data)
        
        if is_overloaded:
            overloaded_faculty.append(fac_data)
            
    # Sort by workload descending
    workload_data.sort(key=lambda x: x["ratio"], reverse=True)
    
    return {
        "faculty_workloads": workload_data,
        "department_summary": {
            "total_assigned_hours": total_department_hours,
            "total_capacity_hours": total_capacity,
            "utilization_percentage": (total_department_hours / max(1, total_capacity)) * 100,
            "overloaded_count": len(overloaded_faculty)
        },
        "overload_alerts": overloaded_faculty
    }

@router.get("/leaves")
def get_leave_report(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns leave summary and trends.
    """
    # All approved leaves for the department
    leaves = db.query(LeaveRequest).join(Faculty).filter(
        Faculty.department_id == current_user.department_id,
        LeaveRequest.status == "APPROVED"
    ).all()
    
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    
    daily_summary = []
    history = []
    faculty_leave_counts = {}
    
    for l in leaves:
        history.append({
            "faculty_name": l.faculty.user.name,
            "start_date": l.start_date,
            "end_date": l.end_date,
            "reason": l.reason,
            "comments": l.comments
        })
        
        if l.faculty.user.name not in faculty_leave_counts:
            faculty_leave_counts[l.faculty.user.name] = 0
        
        # Approximate days
        days = (l.end_date - l.start_date).days + 1 if l.end_date and l.start_date else 1
        faculty_leave_counts[l.faculty.user.name] += days
        
        if l.start_date <= today <= l.end_date:
            daily_summary.append({
                "name": l.faculty.user.name,
                "reason": l.reason
            })
            
    trends = [{"name": name, "days": count} for name, count in faculty_leave_counts.items()]
    trends.sort(key=lambda x: x["days"], reverse=True)
    
    return {
        "daily_summary": daily_summary,
        "leave_trends": trends[:10], # Top 10
        "leave_history": sorted(history, key=lambda x: x["start_date"], reverse=True)[:50]
    }

@router.get("/substitutes")
def get_substitute_report(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns substitute history and fairness tracking.
    """
    allocations = db.query(SubstituteAllocation).join(
        Faculty, SubstituteAllocation.original_faculty_id == Faculty.id
    ).filter(
        Faculty.department_id == current_user.department_id,
        SubstituteAllocation.status == "RESOLVED"
    ).all()
    
    history = []
    substitute_counts = {}
    
    for a in allocations:
        original_name = a.original_faculty.user.name if a.original_faculty else "Unknown"
        sub_name = a.substitute.user.name if a.substitute else "Unknown"
        
        history.append({
            "date": a.date,
            "period": a.period_number,
            "original": original_name,
            "substitute": sub_name,
            "class_group": a.class_group.name if a.class_group else "Unknown"
        })
        
        if sub_name not in substitute_counts:
            substitute_counts[sub_name] = 0
        substitute_counts[sub_name] += 1
        
    fairness = [{"name": name, "times_substituted": count} for name, count in substitute_counts.items()]
    fairness.sort(key=lambda x: x["times_substituted"], reverse=True)
    
    return {
        "substitute_history": sorted(history, key=lambda x: x["date"], reverse=True)[:50],
        "most_assigned": fairness
    }

@router.get("/conflicts")
def get_conflict_report(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns conflict tracking from audit logs.
    """
    # Fetch audit logs related to this HOD's actions (simplification)
    logs = db.query(AuditLog).filter(
        AuditLog.performed_by_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).all()
    
    history = []
    conflict_count = 0
    auto_resolved_count = 0
    
    for log in logs:
        history.append({
            "timestamp": log.timestamp,
            "action": log.action_type,
            "details": log.details
        })
        if "conflict" in log.details.lower():
            conflict_count += 1
        if "auto-resolve" in log.details.lower() or "auto-allocate" in log.details.lower() or "auto_resolve" in log.action_type.lower():
            auto_resolved_count += 1
            
    return {
        "conflict_summary": {
            "total_conflicts_logged": conflict_count,
            "auto_resolved_actions": auto_resolved_count
        },
        "resolution_history": history[:50]
    }

@router.get("/timetable")
def get_master_timetable(db: Session = Depends(get_db), current_user: User = Depends(require_hod)):
    """
    Returns data for master timetable reports (Class-wise, Faculty-wise, Room-wise).
    """
    slots = db.query(TimetableSlot).join(Faculty).filter(
        Faculty.department_id == current_user.department_id
    ).all()
    
    # We will just return raw slots and let the frontend pivot/filter them, 
    # since it's a manageable amount of data (e.g. 300 slots).
    
    formatted_slots = []
    for s in slots:
        formatted_slots.append({
            "id": s.id,
            "day": s.day_of_week,
            "period": s.period_number,
            "class_group": s.class_group.name if s.class_group else "Unknown",
            "class_group_id": s.class_group_id,
            "subject": s.subject.name if s.subject else "Unknown",
            "faculty": s.faculty.user.name if s.faculty and s.faculty.user else "Unknown",
            "faculty_id": s.faculty_id,
            "room": s.classroom.name if s.classroom else "Unknown",
            "room_id": s.classroom_id
        })
        
    return formatted_slots
