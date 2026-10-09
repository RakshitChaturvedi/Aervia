"""
Authentication and User Management Router for Aervia.
Exposes endpoints for registration, login, profile inspection, and role authorization.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import User
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


# Pydantic Schemas
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "public_viewer"  # super_admin, city_officer, field_inspector, public_viewer
    department: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: Optional[str]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserResponse


def seed_default_users():
    """
    Seed initial 4-tier demonstration accounts if not already created.
    """
    db = SessionLocal()
    try:
        default_accounts = [
            ("admin@aervia.gov.in", "Admin123!", "Super Administrator", "super_admin", "Central Technical Ops"),
            ("officer@ghmc.gov.in", "Officer123!", "GHMC City Officer", "city_officer", "GHMC Environmental Wing"),
            ("inspector@ghmc.gov.in", "Inspector123!", "Ward Field Inspector", "field_inspector", "Air Enforcement Squad"),
            ("public@aervia.in", "Public123!", "Public Citizen", "public_viewer", "Public"),
        ]
        for email, password, full_name, role, dept in default_accounts:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                u = User(
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    role=role,
                    department=dept,
                    is_active=True
                )
                db.add(u)
        db.commit()
    except Exception as e:
        print(f"Error seeding default users: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account with assigned role."""
    valid_roles = ["super_admin", "city_officer", "field_inspector", "public_viewer"]
    if req.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{req.role}'. Must be one of: {valid_roles}"
        )

    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    user = User(
        email=req.email.lower().strip(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        department=req.department,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Login with email and password to receive JWT bearer access token."""
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user=UserResponse.model_validate(user)
    )


@router.post("/token", response_model=TokenResponse)
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow compatible token endpoint for Swagger UI."""
    return login(UserLoginRequest(email=form_data.username, password=form_data.password), db)


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Inspect currently authenticated user identity and role."""
    return current_user


@router.get("/verify-role/{role}")
def verify_role_access(role: str, current_user: User = Depends(get_current_user)):
    """Test if current user has permissions for a specific role."""
    has_permission = (current_user.role == role) or (current_user.role == "super_admin")
    return {
        "user_email": current_user.email,
        "assigned_role": current_user.role,
        "tested_role": role,
        "access_granted": has_permission
    }
