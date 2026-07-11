import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.auth.router import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.hod import router as hod_router
from app.routers.hod_reports import router as hod_reports_router
from app.routers.faculty import router as faculty_router
from app.routers.schedule import router as schedule_router
from app.services.ml_predictor import train_burnout_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Initialize database tables
try:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    # Ensure leave_balance column is added
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE faculties ADD COLUMN leave_balance INTEGER DEFAULT 15"))
            conn.commit()
            logger.info("Added leave_balance column to faculties table.")
        except Exception:
            # Already exists or dialect doesn't support it
            pass
            
    # Auto-seed if database is empty of core schedule metadata or has outdated counts
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.schedule import Classroom, Subject
    db = SessionLocal()
    try:
        classroom_count = db.query(Classroom).count()
        subjects_exist = db.query(Subject).first()
        if classroom_count < 11 or not subjects_exist:
            logger.info("Classroom count is low or database is empty. Wiping database cleanly...")
            db.close()
            # Drop and recreate all tables to avoid foreign key violations
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            # Run the seed script directly
            from app.services.seeder import seed_database
            seed_database()
            logger.info("Database seeded successfully.")
    finally:
        try:
            db.close()
        except Exception:
            pass

    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Adaptive Academic Scheduling Platform API Core",
    version="1.0.0"
)

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response

class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            origin = request.headers.get("Origin") or request.headers.get("origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, bypass-tunnel-reminder"
            return response
            
        response = await call_next(request)
        origin = request.headers.get("Origin") or request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, bypass-tunnel-reminder"
        return response

app.add_middleware(CustomCORSMiddleware)

# Startup events
@app.on_event("startup")
def startup_event():
    # Train the lightweight scikit-learn burnout prediction model
    logger.info("Starting up ML engine...")
    train_burnout_model()
    logger.info("ML engine startup complete.")

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(hod_router)
app.include_router(hod_reports_router)
app.include_router(faculty_router)
app.include_router(schedule_router)

@app.get("/")
def read_root():
    return {
        "status": "ONLINE",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }
