from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.dependencies import get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications")
templates = Jinja2Templates(directory="app/templates")


def get_unread_count(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        return 0
    db = SessionLocal()
    try:
        return db.query(Notification).filter_by(user_id=user_id, is_read=False).count()
    finally:
        db.close()


@router.get("")
def list_notifications(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    notifications = (
        db.query(Notification)
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    for n in notifications:
        n.is_read = True
    db.commit()

    return templates.TemplateResponse(
        "notifications/index.html",
        {"request": request, "notifications": notifications, "current_user": current_user},
    )


@router.post("/mark-read")
def mark_read(request: Request, notification_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    n = db.query(Notification).filter_by(id=notification_id, user_id=current_user.id).first()
    if n:
        n.is_read = True
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)
