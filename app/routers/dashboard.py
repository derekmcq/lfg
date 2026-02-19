from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.post import Post
from app.models.membership import Membership

router = APIRouter(prefix="/dashboard")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    my_posts = db.query(Post).filter(Post.author_id == current_user.id).order_by(Post.created_at.desc()).all()
    for post in my_posts:
        post.accepted_count = db.query(Membership).filter_by(post_id=post.id, status="accepted").count()

    joined_groups = (
        db.query(Membership)
        .filter_by(user_id=current_user.id, status="accepted")
        .all()
    )
    pending_requests = (
        db.query(Membership)
        .filter_by(user_id=current_user.id, status="pending")
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "current_user": current_user,
            "my_posts": my_posts,
            "joined_groups": joined_groups,
            "pending_requests": pending_requests,
        },
    )
