import os
import sys
from collections import defaultdict
from ortools.sat.python import cp_model

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup

def debug_solve():
    db = SessionLocal()
    try:
        faculties = db.query(Faculty).all()
        subjects = db.query(Subject).all()
        classrooms = db.query(Classroom).all()
        class_groups = db.query(ClassGroup).all()
        
        DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        PERIODS = [1, 2, 3, 4, 5, 6]
        
        model = cp_model.CpModel()
        variables = {}
        
        qualified_facs_for_subject = defaultdict(list)
        for f in faculties:
            for s in f.qualified_subjects:
                qualified_facs_for_subject[s.id].append(f.id)
                
        # 1. Create variables
        for d in DAYS:
            for p in PERIODS:
                for c in class_groups:
                    for s in subjects:
                        if c.department_id != s.department_id:
                            continue
                        eligible_facs = qualified_facs_for_subject[s.id]
                        for f_id in eligible_facs:
                            for r in classrooms:
                                key = (d, p, c.id, f_id, s.id, r.id)
                                variables[key] = model.NewBoolVar(f"x_{d}_{p}_{c.id}_{f_id}_{s.id}_{r.id}")
                                
        # Constraint 1: A class has at most 1 slot per period
        for d in DAYS:
            for p in PERIODS:
                for c in class_groups:
                    slots = [variables[k] for k in variables if k[0] == d and k[1] == p and k[2] == c.id]
                    model.AddAtMostOne(slots)
                    
        # Constraint 2: A faculty teaches at most 1 class at a time
        for d in DAYS:
            for p in PERIODS:
                for f in faculties:
                    slots = [variables[k] for k in variables if k[0] == d and k[1] == p and k[3] == f.id]
                    model.AddAtMostOne(slots)
                    
        # Constraint 3: A room hosts at most 1 class at a time
        for d in DAYS:
            for p in PERIODS:
                for r in classrooms:
                    slots = [variables[k] for k in variables if k[0] == d and k[1] == p and k[5] == r.id]
                    model.AddAtMostOne(slots)
                    
        # Constraint 4: Subject hours satisfied
        for c in class_groups:
            for s in subjects:
                if c.department_id != s.department_id:
                    continue
                slots = [variables[k] for k in variables if k[2] == c.id and k[4] == s.id]
                if slots:
                    model.Add(sum(slots) == s.hours_required_per_week)
                else:
                    print(f"⚠️ Warning: No variables created for Class {c.name} and Subject {s.code}")
                    
        # Constraint 5: Faculty max hours
        for f in faculties:
            slots = [variables[k] for k in variables if k[3] == f.id]
            if slots:
                model.Add(sum(slots) <= f.max_hours_per_week)
                
        # Run solver with log logging enabled
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0
        solver.parameters.log_search_progress = True
        
        print("\nCalling solver...")
        status = solver.Solve(model)
        print(f"\nSolver Status: {solver.StatusName(status)}")
        if status == cp_model.INFEASIBLE:
            print("Model is INFEASIBLE.")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_solve()
