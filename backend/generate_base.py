import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.solver import generate_base_timetable

def run():
    print("Computing base timetable layout via Google OR-Tools CP-SAT...")
    db = SessionLocal()
    try:
        res = generate_base_timetable(db)
        print("Solver response:", res)
    except Exception as e:
        print("Error running solver:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run()
