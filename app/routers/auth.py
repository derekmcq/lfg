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
    return templates.TemplateResponse("auth/register.html", {"request": request, "form": {}})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    form = {"username": username, "email": email}
    if db.query(User).filter(User.username == username).first():
        flash(request, "Username already taken.", "danger")
        return templates.TemplateResponse("auth/register.html", {"request": request, "form": form})
    if db.query(User).filter(User.email == email).first():
        flash(request, "Email already registered.", "danger")
        return templates.TemplateResponse("auth/register.html", {"request": request, "form": form})
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
