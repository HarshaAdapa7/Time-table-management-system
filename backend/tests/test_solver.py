import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.models.user import User
from app.models.schedule import Department, Faculty, Subject, Classroom, ClassGroup, TimetableSlot
from app.auth.jwt import get_password_hash
from app.services.solver import generate_base_timetable
from app.services.recommender import score_substitute_candidates

# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="db")
def fixture_db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed minimal test data
    dept = Department(name="Test Department")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    
    classroom = Classroom(name="Test Room", room_number="R-101", capacity=30)
    db.add(classroom)
    
    subject = Subject(code="T-101", name="Test Subject", department_id=dept.id, hours_required_per_week=2)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    
    class_group = ClassGroup(name="Class-A", department_id=dept.id)
    db.add(class_group)
    
    user1 = User(
        email="teacher1@test.edu",
        name="Teacher One",
        hashed_password=get_password_hash("password"),
        role="FACULTY",
        department_id=dept.id
    )
    db.add(user1)
    db.commit()
    db.refresh(user1)
    
    faculty1 = Faculty(
        user_id=user1.id,
        department_id=dept.id,
        max_hours_per_week=10,
        current_workload=0.0
    )
    faculty1.qualified_subjects.append(subject)
    db.add(faculty1)
    
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_generate_base_timetable(db):
    result = generate_base_timetable(db)
    assert result["status"] == "SUCCESS"
    assert result["slots_created"] == 2 # hours_required_per_week for subject is 2
    
    slots = db.query(TimetableSlot).all()
    assert len(slots) == 2
    for slot in slots:
        assert slot.subject.code == "T-101"
        assert slot.faculty.user.name == "Teacher One"

def test_substitute_recommender(db):
    # Generate base timetable
    generate_base_timetable(db)
    
    # We should have a teacher free on other periods
    # Let's check candidates for T-101 on a day/period where teacher is not teaching
    import datetime
    today = datetime.date.today()
    day_str = today.strftime("%A")
    
    # Find a period where teacher is teaching
    taken_slot = db.query(TimetableSlot).first()
    taken_period = taken_slot.period_number
    taken_day = taken_slot.day_of_week
    
    # Candidate should NOT be available on the taken slot
    candidates_taken = score_substitute_candidates(db, taken_slot.subject_id, taken_day, taken_period, today)
    assert len(candidates_taken) == 0 # because teacher is already teaching in this slot
    
    # Candidate SHOULD be available on another period
    free_period = (taken_period % 6) + 1
    candidates_free = score_substitute_candidates(db, taken_slot.subject_id, taken_day, free_period, today)
    assert len(candidates_free) == 1
    assert candidates_free[0]["name"] == "Teacher One"
