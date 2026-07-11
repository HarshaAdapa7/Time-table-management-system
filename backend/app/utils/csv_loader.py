import io
import pandas as pd
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup, faculty_subjects
from app.auth.jwt import get_password_hash

def load_classroom_csv(db: Session, csv_data: str) -> int:
    df = pd.read_csv(io.StringIO(csv_data))
    # Expected columns: name, room_number, capacity
    count = 0
    for _, row in df.iterrows():
        room_num = str(row['room_number']).strip()
        existing = db.query(Classroom).filter(Classroom.room_number == room_num).first()
        if existing:
            existing.name = str(row['name']).strip()
            existing.capacity = int(row['capacity'])
        else:
            room = Classroom(
                name=str(row['name']).strip(),
                room_number=room_num,
                capacity=int(row['capacity'])
            )
            db.add(room)
            count += 1
    db.commit()
    return count

def load_subjects_csv(db: Session, csv_data: str) -> int:
    df = pd.read_csv(io.StringIO(csv_data))
    # Expected columns: code, name, department_name, hours_per_week
    count = 0
    for _, row in df.iterrows():
        code = str(row['code']).strip().upper()
        dept_name = str(row['department_name']).strip()
        
        # Find or create department
        dept = db.query(Department).filter(Department.name == dept_name).first()
        if not dept:
            dept = Department(name=dept_name)
            db.add(dept)
            db.commit()
            db.refresh(dept)
            
        existing = db.query(Subject).filter(Subject.code == code).first()
        if existing:
            existing.name = str(row['name']).strip()
            existing.department_id = dept.id
            existing.hours_required_per_week = int(row['hours_per_week'])
        else:
            sub = Subject(
                code=code,
                name=str(row['name']).strip(),
                department_id=dept.id,
                hours_required_per_week=int(row['hours_per_week'])
            )
            db.add(sub)
            count += 1
    db.commit()
    return count

def load_classes_csv(db: Session, csv_data: str) -> int:
    df = pd.read_csv(io.StringIO(csv_data))
    # Expected columns: name, department_name
    count = 0
    for _, row in df.iterrows():
        name = str(row['name']).strip()
        dept_name = str(row['department_name']).strip()
        
        dept = db.query(Department).filter(Department.name == dept_name).first()
        if not dept:
            dept = Department(name=dept_name)
            db.add(dept)
            db.commit()
            db.refresh(dept)
            
        existing = db.query(ClassGroup).filter(ClassGroup.name == name).first()
        if existing:
            existing.department_id = dept.id
        else:
            cls = ClassGroup(
                name=name,
                department_id=dept.id
            )
            db.add(cls)
            count += 1
    db.commit()
    return count

def load_faculty_csv(db: Session, csv_data: str) -> int:
    df = pd.read_csv(io.StringIO(csv_data))
    # Expected columns: name, email, role, department_name, max_hours, qualified_subjects (comma-sep codes)
    count = 0
    for _, row in df.iterrows():
        email = str(row['email']).strip().lower()
        dept_name = str(row['department_name']).strip()
        name = str(row['name']).strip()
        role = str(row['role']).strip().upper()  # ADMIN, HOD, COORDINATOR, FACULTY
        max_hours = int(row.get('max_hours', 16))
        
        # Valid roles
        if role not in ["ADMIN", "HOD", "COORDINATOR", "FACULTY"]:
            role = "FACULTY"
            
        dept = db.query(Department).filter(Department.name == dept_name).first()
        if not dept:
            dept = Department(name=dept_name)
            db.add(dept)
            db.commit()
            db.refresh(dept)
            
        # Find or create User
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                name=name,
                hashed_password=get_password_hash("Password@123"), # Default login password
                role=role,
                department_id=dept.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Find or create Faculty profile
        faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        if not faculty:
            faculty = Faculty(
                user_id=user.id,
                department_id=dept.id,
                max_hours_per_week=max_hours
            )
            db.add(faculty)
            db.commit()
            db.refresh(faculty)
            count += 1
        else:
            faculty.department_id = dept.id
            faculty.max_hours_per_week = max_hours
            
        # Associate qualified subjects
        if 'qualified_subjects' in row and pd.notna(row['qualified_subjects']):
            subject_codes = [c.strip().upper() for c in str(row['qualified_subjects']).split(",") if c.strip()]
            qualified_subs = db.query(Subject).filter(Subject.code.in_(subject_codes)).all()
            faculty.qualified_subjects = qualified_subs
            
    db.commit()
    return count
