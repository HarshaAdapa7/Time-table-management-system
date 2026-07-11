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
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Adaptive Academic Scheduling Platform API Core",
    version="1.0.0"
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
