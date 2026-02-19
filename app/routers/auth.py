import re

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.auth_utils import hash_password, verify_password
from app.flash import flash

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="app/templates")


@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request, "form": {}, "errors": {}})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    form = {"username": username, "email": email, "password": password}
    errors = {}

    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        errors["username"] = "Username may only contain letters, numbers, and underscores."
    elif db.query(User).filter(User.username == username).first():
        errors["username"] = "Username already taken."

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors["email"] = "Enter a valid email address."
    elif db.query(User).filter(User.email == email).first():
        errors["email"] = "Email already registered."

    if not (8 <= len(password) <= 24):
        errors["password"] = "Password must be 8–24 characters."
    elif not re.search(r"[A-Z]", password):
        errors["password"] = "Password must contain at least one uppercase letter."
    elif not re.search(r"[a-z]", password):
        errors["password"] = "Password must contain at least one lowercase letter."
    elif not re.search(r"\d", password):
        errors["password"] = "Password must contain at least one number."
    elif not re.search(r"[^A-Za-z0-9]", password):
        errors["password"] = "Password must contain at least one symbol."

    if errors:
        return templates.TemplateResponse("auth/register.html", {"request": request, "form": form, "errors": errors})
    user = User(username=username, email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    flash(request, f"Welcome, {user.username}!", "success")
    return RedirectResponse(url="/posts", status_code=303)


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request, "form": {}})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        flash(request, "Invalid username or password.", "danger")
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "form": {"username": username}}
        )
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    flash(request, f"Welcome back, {user.username}!", "success")
    return RedirectResponse(url="/posts", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
