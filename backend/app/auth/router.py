from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.jwt import verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.schedule import Faculty
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    email: str
    department_id: int | None = None
    department_name: str | None = None
    faculty_id: int | None = None

class UserMeResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    department_id: int | None = None
    department_name: str | None = None
    faculty_id: int | None = None

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Query faculty ID if user is faculty
    faculty_id = None
    if user.role in ["FACULTY", "COORDINATOR", "HOD"]:
        fac = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        if fac:
            faculty_id = fac.id
            
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "faculty_id": faculty_id
    }

@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    faculty_id = None
    if current_user.role in ["FACULTY", "COORDINATOR", "HOD"]:
        fac = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
        if fac:
            faculty_id = fac.id
            
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "department_id": current_user.department_id,
        "department_name": current_user.department.name if current_user.department else None,
        "faculty_id": faculty_id
    }
