from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.post import Post
from app.models.membership import Membership
from app.models.notification import Notification
from app.flash import flash

router = APIRouter(prefix="/posts")


def _notify(db, user_id: int, message: str, link: str = None):
    db.add(Notification(user_id=user_id, message=message, link=link))


templates = Jinja2Templates(directory="app/templates")


@router.post("/{post_id}/request")
def request_join(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return RedirectResponse(url="/posts", status_code=303)

    if post.author_id == current_user.id:
        flash(request, "You cannot request to join your own post.", "warning")
        return RedirectResponse(url=f"/posts/{post_id}", status_code=303)

    existing = db.query(Membership).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        if existing.status in ("pending", "accepted"):
            return RedirectResponse(url=f"/posts/{post_id}", status_code=303)
        # denied — allow re-request by updating row
        existing.status = "pending"
        existing.requested_at = datetime.now(timezone.utc)
        existing.responded_at = None
        _notify(db, post.author_id, f"{current_user.username} requested to join your {post.game} group", f"/posts/{post_id}/requests")
        db.commit()
        flash(request, "Re-request sent!", "success")
        return RedirectResponse(url=f"/posts/{post_id}", status_code=303)

    accepted = db.query(Membership).filter_by(post_id=post_id, status="accepted").count()
    if accepted + 1 >= post.max_players:
        flash(request, "Group is full.", "warning")
        return RedirectResponse(url=f"/posts/{post_id}", status_code=303)

    m = Membership(user_id=current_user.id, post_id=post_id, status="pending")
    db.add(m)
    _notify(db, post.author_id, f"{current_user.username} requested to join your {post.game} group", f"/posts/{post_id}/requests")
    db.commit()
    flash(request, "Join request sent!", "success")
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{post_id}/withdraw")
def withdraw_request(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    m = db.query(Membership).filter_by(user_id=current_user.id, post_id=post_id, status="pending").first()
    if m:
        db.delete(m)
        db.commit()
        flash(request, "Request withdrawn.", "info")
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{post_id}/leave")
def leave_group(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    m = db.query(Membership).filter_by(user_id=current_user.id, post_id=post_id, status="accepted").first()
    if m:
        db.delete(m)
        db.commit()
        flash(request, "You have left the group.", "info")
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.get("/{post_id}/requests")
def list_requests(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not found or not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)

    pending = db.query(Membership).filter_by(post_id=post_id, status="pending").all()
    return templates.TemplateResponse(
        "posts/requests.html",
        {"request": request, "post": post, "requests": pending, "current_user": current_user},
    )


@router.post("/{post_id}/requests/{membership_id}/accept")
def accept_request(request: Request, post_id: int, membership_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)

    accepted = db.query(Membership).filter_by(post_id=post_id, status="accepted").count()
    if accepted + 1 >= post.max_players:
        flash(request, "Group is already full.", "warning")
        return RedirectResponse(url=f"/posts/{post_id}/requests", status_code=303)

    m = db.query(Membership).filter_by(id=membership_id, post_id=post_id).first()
    if m:
        m.status = "accepted"
        m.responded_at = datetime.now(timezone.utc)
        _notify(db, m.user_id, f"Your request to join {post.game} was accepted!", f"/posts/{post_id}")
        db.commit()
        flash(request, f"{m.user.username} accepted!", "success")
    return RedirectResponse(url=f"/posts/{post_id}/requests", status_code=303)


@router.post("/{post_id}/requests/{membership_id}/deny")
def deny_request(request: Request, post_id: int, membership_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)

    m = db.query(Membership).filter_by(id=membership_id, post_id=post_id).first()
    if m:
        m.status = "denied"
        m.responded_at = datetime.now(timezone.utc)
        _notify(db, m.user_id, f"Your request to join {post.game} was denied.", f"/posts/{post_id}")
        db.commit()
        flash(request, f"{m.user.username} denied.", "info")
    return RedirectResponse(url=f"/posts/{post_id}/requests", status_code=303)
