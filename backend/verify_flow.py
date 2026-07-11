import os
import sys
import datetime

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup, TimetableSlot
from app.models.leave import LeaveRequest, SubstituteAllocation
from app.services.solver import generate_base_timetable, resolve_leave_substitutions
from app.services.recommender import score_substitute_candidates

def run_verification():
    print("==================================================")
    print("   Verification Simulation: End-to-End Flow")
    print("==================================================")
    
    # 1. Reset database tables
    print("\n[Step 1] Resetting and initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 2. Seed departments
        csd_dept = Department(name="Computer Science & Design")
        ece_dept = Department(name="Electronics & Communication")
        db.add_all([csd_dept, ece_dept])
        db.commit()
        db.refresh(csd_dept)
        db.refresh(ece_dept)
        
        # 3. Seed Classrooms
        lh301 = Classroom(name="CSD LH 1", room_number="LH-301", capacity=60)
        lh302 = Classroom(name="CSD LH 2", room_number="LH-302", capacity=60)
        db.add_all([lh301, lh302])
        db.commit()
        db.refresh(lh301)
        db.refresh(lh302)

        # 4. Seed Subjects
        csd101 = Subject(code="CSD-101", name="Intro to Data Science", department_id=csd_dept.id, hours_required_per_week=4)
        csd102 = Subject(code="CSD-102", name="Machine Learning", department_id=csd_dept.id, hours_required_per_week=4)
        db.add_all([csd101, csd102])
        db.commit()
        db.refresh(csd101)
        db.refresh(csd102)

        # 5. Seed Class Groups
        class_a = ClassGroup(name="CSD-3A", department_id=csd_dept.id)
        db.add(class_a)
        db.commit()
        db.refresh(class_a)

        # 6. Seed HOD
        hod_user = User(
            email="hod_csd@anits.edu.in",
            name="Prof. Adinarayana Salina",
            hashed_password="hashed",
            role="HOD",
            department_id=csd_dept.id
        )
        db.add(hod_user)
        db.commit()
        db.refresh(hod_user)
        
        hod_profile = Faculty(
            user_id=hod_user.id,
            department_id=csd_dept.id,
            max_hours_per_week=16,
            current_workload=0.0
        )
        hod_profile.qualified_subjects.append(csd101)
        db.add(hod_profile)
        
        # Seed Faculty 1 (Dr. I. Sundara Siva Rao)
        fac1_user = User(
            email="sivarao.csd@anits.edu.in",
            name="Dr.I.Sundara Siva Rao",
            hashed_password="hashed",
            role="FACULTY",
            department_id=csd_dept.id
        )
        db.add(fac1_user)
        db.commit()
        db.refresh(fac1_user)
        
        fac1_profile = Faculty(
            user_id=fac1_user.id,
            department_id=csd_dept.id,
            max_hours_per_week=16,
            current_workload=0.0
        )
        fac1_profile.qualified_subjects.append(csd102)
        db.add(fac1_profile)
        
        # Seed Faculty 2 (Dr. Om Prakash Samantray - Qualified for BOTH to act as substitute)
        fac2_user = User(
            email="omprakash.csd@anits.edu.in",
            name="Dr. Om Prakash Samantray",
            hashed_password="hashed",
            role="FACULTY",
            department_id=csd_dept.id
        )
        db.add(fac2_user)
        db.commit()
        db.refresh(fac2_user)
        
        fac2_profile = Faculty(
            user_id=fac2_user.id,
            department_id=csd_dept.id,
            max_hours_per_week=16,
            current_workload=0.0
        )
        fac2_profile.qualified_subjects.extend([csd101, csd102])
        db.add(fac2_profile)
        
        db.commit()
        
        # 7. Generate Base Timetable
        print("\n[Step 2] Computing base timetable using CP-SAT Solver...")
        base_res = generate_base_timetable(db)
        print(f"-> Base Solver Status: {base_res['status']}, Slots Created: {base_res.get('slots_created', 0)}")
        
        # Retrieve and print the initial slots
        initial_slots = db.query(TimetableSlot).all()
        print("\n--- Initial Timetable Slots ---")
        for s in initial_slots:
            print(f"Day: {s.day_of_week} | Period: {s.period_number} | Class: {s.class_group.name} | Subj: {s.subject.code} | Faculty: {s.faculty.user.name}")

        # Choose a target slot dynamically to perform leave on
        target_slot = db.query(TimetableSlot).first()
        if not target_slot:
            print("Error: No timetable slot found. Cannot proceed with leave test.")
            return

        target_fac_profile = db.query(Faculty).filter(Faculty.id == target_slot.faculty_id).first()

        print(f"\n[Step 3] Simulating Faculty Leave Request...")
        print(f"{target_fac_profile.user.name} requests leave for {target_slot.day_of_week}, Period {target_slot.period_number} due to Medical Checkup.")
        
        # Create approved leave request
        tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
        # Ensure tomorrow is mapped to the target day of week
        weekday_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        target_weekday_idx = weekday_map[target_slot.day_of_week]
        
        # Find next date with this weekday
        days_ahead = target_weekday_idx - tomorrow_date.weekday()
        if days_ahead < 0:
            days_ahead += 7
        leave_date = tomorrow_date + datetime.timedelta(days=days_ahead)
        
        leave_req = LeaveRequest(
            faculty_id=target_fac_profile.id,
            start_date=leave_date,
            end_date=leave_date,
            specific_periods=str(target_slot.period_number),
            status="PENDING",
            reason="Medical Checkup"
        )
        db.add(leave_req)
        db.commit()
        db.refresh(leave_req)
        
        # 8. Approve Leave (Triggers Incremental Re-optimization)
        print("\n[Step 4] HOD Approving Leave & Triggering Substitute Allocator...")
        leave_req.status = "APPROVED"
        leave_req.approved_by_id = hod_user.id
        db.commit()
        
        # Trigger solver repair
        repair_res = resolve_leave_substitutions(db, leave_req.id)
        print(f"-> Allocator Status: {repair_res['status']}, Resolved Slots: {repair_res.get('resolved_slots', 0)}")
        
        # 9. Verify allocation in database
        allocation = db.query(SubstituteAllocation).filter(SubstituteAllocation.leave_request_id == leave_req.id).first()
        if allocation:
            print("\n==================================================")
            print("   [SUCCESS] DYNAMIC TIMETABLE REPAIR SUCCESSFUL!")
            print("==================================================")
            print(f"Date: {allocation.date} ({target_slot.day_of_week})")
            print(f"Period: {allocation.period_number}")
            print(f"Class Affected: {allocation.class_group.name}")
            print(f"Original Faculty: {target_slot.faculty.user.name} (ON LEAVE)")
            print(f"Assigned Substitute: {allocation.substitute.user.name if allocation.substitute_id else 'NONE'}")
            print(f"Reasoning/Score: {allocation.explanation}")
            print("==================================================")
        else:
            print("[FAILURE] No SubstituteAllocation record was created.")

    except Exception as e:
        print(f"Verification crashed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
