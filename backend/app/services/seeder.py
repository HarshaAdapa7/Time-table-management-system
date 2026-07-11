import os
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.auth.jwt import get_password_hash
from app.models.user import User
from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup

def seed_database():
    print("Seeding database with actual CSD faculty...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Create Departments
        csd_dept = db.query(Department).filter(Department.name == "Computer Science & Design").first()
        if not csd_dept:
            csd_dept = Department(name="Computer Science & Design")
            db.add(csd_dept)
            db.commit()
            db.refresh(csd_dept)
            print(f"Created Department: {csd_dept.name}")
            
        ece_dept = db.query(Department).filter(Department.name == "Electronics & Communication").first()
        if not ece_dept:
            ece_dept = Department(name="Electronics & Communication")
            db.add(ece_dept)
            db.commit()
            db.refresh(ece_dept)
            print(f"Created Department: {ece_dept.name}")

        # 2. Create Admin
        admin_email = "admin@timetable.edu"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                name="System Administrator",
                hashed_password=get_password_hash("Admin@12345"),
                role="ADMIN",
                department_id=None
            )
            db.add(admin)
            print("Created Admin account: admin@timetable.edu")
            
        # 3. Create Classrooms
        rooms_data = [
            ("CSD Lecture Hall 1", "LH-301", 60),
            ("CSD Lecture Hall 2", "LH-302", 60),
            ("CSD Lecture Hall 3", "LH-303", 60),
            ("CSD Lecture Hall 4", "LH-304", 60),
            ("CSD Lecture Hall 5", "LH-305", 60),
            ("CSD Lecture Hall 6", "LH-306", 60),
            ("CSD Seminar Hall", "SH-301", 120),
            ("Data Science Lab 1", "DL-301", 50),
            ("Data Science Lab 2", "DL-302", 50),
            ("ECE Lecture Hall 1", "LH-201", 60),
            ("ECE Lecture Hall 2", "LH-202", 60)
        ]
        
        for name, num, cap in rooms_data:
            existing = db.query(Classroom).filter(Classroom.room_number == num).first()
            if not existing:
                room = Classroom(name=name, room_number=num, capacity=cap)
                db.add(room)
                print(f"Created Classroom: {num}")
                
        # 4. Create Subjects
        subjects_data = [
            ("CSD-101", "Introduction to Data Science", csd_dept.id, 5),
            ("CSD-102", "Machine Learning Foundation", csd_dept.id, 5),
            ("CSD-103", "Data Visualization Techniques", csd_dept.id, 4),
            ("CSD-104", "Big Data Analytics", csd_dept.id, 4),
            ("CSD-105", "Artificial Intelligence Fundamentals", csd_dept.id, 5),
            ("EC-101", "Digital Electronics", ece_dept.id, 6),
            ("EC-102", "Signals & Systems", ece_dept.id, 6)
        ]
        
        subjects_map = {}
        for code, name, dept_id, hours in subjects_data:
            existing = db.query(Subject).filter(Subject.code == code).first()
            if not existing:
                subject = Subject(code=code, name=name, department_id=dept_id, hours_required_per_week=hours)
                db.add(subject)
                db.commit()
                db.refresh(subject)
                subjects_map[code] = subject
                print(f"Created Subject: {name} ({code})")
            else:
                subjects_map[code] = existing
                
        # 5. Create Class Groups
        classes_data = [
            ("CSD-1st Year A", csd_dept.id),
            ("CSD-1st Year B", csd_dept.id),
            ("CSD-2nd Year A", csd_dept.id),
            ("CSD-2nd Year B", csd_dept.id),
            ("CSD-3rd Year A", csd_dept.id),
            ("CSD-3rd Year B", csd_dept.id),
            ("CSD-4th Year A", csd_dept.id),
            ("CSD-4th Year B", csd_dept.id),
            ("ECE-1st Year A", ece_dept.id),
            ("ECE-2nd Year A", ece_dept.id)
        ]
        
        for name, dept_id in classes_data:
            existing = db.query(ClassGroup).filter(ClassGroup.name == name).first()
            if not existing:
                cls = ClassGroup(name=name, department_id=dept_id)
                db.add(cls)
                print(f"Created Class Group: {name}")
                
        db.commit()

        # 6. Seed all 28 Actual Faculty members for CSD department
        csd_faculties_input = [
            ("Prof. Adinarayana Salina", "hod_csd@anits.edu.in", "HOD"),
            ("Dr.I.Sundara Siva Rao", "sivarao.csd@anits.edu.in", "FACULTY"),
            ("Dr. Om Prakash Samantray", "omprakash.csd@anits.edu.in", "FACULTY"),
            ("Dr. S V S Santhi", "svssanthi.csd@anits.edu.in", "FACULTY"),
            ("Dr.I.S.Srinivasa Rao", "srinivasarao.csd@anits.edu.in", "FACULTY"),
            ("Dr J. Aruna Devi", "jarunadevi2003.csd@anits.edu.in", "FACULTY"),
            ("Mrs G V Gayathri", "gvgayathri.csd@anits.edu.in", "FACULTY"),
            ("Mrs.Prathi Naveena", "pnaveena.csd@anits.edu.in", "FACULTY"),
            ("Mrs. T Mallika", "mallika.csd@anits.edu.in", "FACULTY"),
            ("Mrs. Botta Venkata Kavya", "kavyabotta.csd@anits.edu.in", "FACULTY"),
            ("Ms. R.Anantha", "r.anantha.csd@anits.edu.in", "FACULTY"),
            ("Mrs. B. Sujatha", "bsujatha.csd@anits.edu.in", "FACULTY"),
            ("Mrs. M.Bhavya", "bhavyam.csd@anits.edu.in", "FACULTY"),
            ("Mrs. A Bhagya Lakshmi", "bhagyalakshmi.csd@anits.edu.in", "FACULTY"),
            ("Mrs. Iddum Swathi", "iswathi.csd@anits.edu.in", "FACULTY"),
            ("Dr. Y Bheem Shankar", "shankaryaga.csd@anits.edu.in", "FACULTY"),
            ("Mr G.Naveen", "naveengosu.csd@anits.edu.in", "FACULTY"),
            ("Mr. Y Satish Kumar", "satishyanamadala.csd@anits.edu.in", "FACULTY"),
            ("Ms.B.Renuka Sai", "renukabantupalli.csd@anits.edu.in", "FACULTY"),
            ("Mr P. Uday Bhaskar", "udayp.csd@anits.edu.in", "FACULTY"),
            ("Mrs.K.Venkat Lakshmi", "kvlakshmi.csd@anits.edu.in", "FACULTY"),
            ("Mr.Seetayya Narthu", "seethn.csd@anits.edu.in", "FACULTY"),
            ("Mrs S. Aruna Jyothi", "sarunajyothi.csd@anits.edu.in", "FACULTY"),
            ("Ms. Imandi Tejaswini", "itejaswini.csd@anits.edu.in", "FACULTY"),
            ("Mrs. K Sowjanya Naidu", "sowjanyak.csd@anits.edu.in", "FACULTY"),
            ("Mrs.Pinnamraju T.S.Priya", "ptspriya.csd@anits.edu.in", "FACULTY"),
            ("Dr.B.Vasantha Rani", "vasantharani.csd@anits.edu.in", "FACULTY"),
            ("Pyla Uma", "pylauma.csd@anits.edu.in", "FACULTY")
        ]

        csd_subjects = db.query(Subject).filter(Subject.department_id == csd_dept.id).all()
        
        for idx, (name, email, role) in enumerate(csd_faculties_input):
            # Create user
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    name=name,
                    hashed_password=get_password_hash("Password@123"), # Default demo password
                    role=role,
                    department_id=csd_dept.id
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
            # Create faculty profile
            faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
            if not faculty:
                faculty = Faculty(
                    user_id=user.id,
                    department_id=csd_dept.id,
                    max_hours_per_week=16,
                    current_workload=0.0
                )
                
                # Assign subsets of qualified subjects to model diverse expertise
                if idx % 5 == 0:
                    faculty.qualified_subjects = [subjects_map["CSD-101"], subjects_map["CSD-103"]]
                elif idx % 5 == 1:
                    faculty.qualified_subjects = [subjects_map["CSD-102"], subjects_map["CSD-105"]]
                elif idx % 5 == 2:
                    faculty.qualified_subjects = [subjects_map["CSD-104"], subjects_map["CSD-102"], subjects_map["CSD-101"]]
                elif idx % 5 == 3:
                    faculty.qualified_subjects = [subjects_map["CSD-103"], subjects_map["CSD-104"]]
                else:
                    faculty.qualified_subjects = [subjects_map["CSD-105"], subjects_map["CSD-101"]]
                    
                db.add(faculty)
                print(f"Seeded faculty: {name} ({role})")

        # 7. Seed Lab Assistants (ASSISTANT role)
        assistants_data = [
            ("Mr. Chandra CSD Lab Tech", "chandra.csd@anits.edu.in", "ASSISTANT"),
            ("Mr. Surya CSD Lab Tech", "surya.csd@anits.edu.in", "ASSISTANT")
        ]
        for name, email, role in assistants_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    name=name,
                    hashed_password=get_password_hash("Password@123"),
                    role=role,
                    department_id=csd_dept.id
                )
                db.add(user)
                print(f"Seeded Lab Assistant: {name}")

        # 8. Seed Non-Teaching Staff (NON_TEACHING role)
        staff_data = [
            ("Mr. Sekhar CSD Admin Coordinator", "sekhar.csd@anits.edu.in", "NON_TEACHING"),
            ("Mr. Ramesh CSD Office Clerk", "ramesh.csd@anits.edu.in", "NON_TEACHING")
        ]
        for name, email, role in staff_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    name=name,
                    hashed_password=get_password_hash("Password@123"),
                    role=role,
                    department_id=csd_dept.id
                )
                db.add(user)
                print(f"Seeded Non-Teaching Staff: {name}")

        # 9. Seed ECE Faculty (mocked automatically)
        ece_faculty_names = ["Dr. Claude Shannon", "Dr. Heinrich Hertz"]
        for idx, name in enumerate(ece_faculty_names):
            clean_name_lower = name.lower().replace("dr.", "").replace(" ", "").strip()
            email = f"{clean_name_lower}@anits.edu.in"
            
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    name=name,
                    hashed_password=get_password_hash("Password@123"),
                    role="FACULTY",
                    department_id=ece_dept.id
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
            faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
            if not faculty:
                faculty = Faculty(
                    user_id=user.id,
                    department_id=ece_dept.id,
                    max_hours_per_week=16,
                    current_workload=0.0
                )
                if idx == 0:
                    faculty.qualified_subjects = [subjects_map["EC-101"], subjects_map["EC-102"]]
                else:
                    faculty.qualified_subjects = [subjects_map["EC-101"]]
                db.add(faculty)
                
        db.commit()
        print("Database seeded successfully with all roles!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()
