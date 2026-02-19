from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.post import Post
from app.models.membership import Membership
from app.schemas.post import VALID_PLATFORMS
from app.flash import flash
from better_profanity import profanity

router = APIRouter(prefix="/posts")
templates = Jinja2Templates(directory="app/templates")


def _accepted_count(db: Session, post_id: int) -> int:
    return db.query(Membership).filter_by(post_id=post_id, status="accepted").count()


@router.get("")
def list_posts(
    request: Request,
    game: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    query = db.query(Post)
    if game:
        query = query.filter(Post.game.ilike(f"%{game}%"))
    if platform:
        query = query.filter(Post.platform.contains(platform))
    posts = query.order_by(Post.created_at.desc()).all()

    for post in posts:
        post.accepted_count = _accepted_count(db, post.id)

    return templates.TemplateResponse(
        "posts/index.html",
        {
            "request": request,
            "posts": posts,
            "platforms": VALID_PLATFORMS,
            "filter_game": game,
            "filter_platform": platform,
            "current_user": current_user,
        },
    )


@router.get("/new")
def new_post_form(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(
        "posts/create.html",
        {"request": request, "platforms": VALID_PLATFORMS, "form": {}, "errors": {}, "current_user": current_user},
    )


@router.post("/new")
def create_post(
    request: Request,
    game: str = Form(...),
    platform: list[str] = Form(...),
    description: str = Form(...),
    max_players: int = Form(4),
    scheduled_at: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    errors = {}
    if profanity.contains_profanity(description):
        errors["description"] = "Description contains inappropriate language."

    if errors:
        form = {"game": game, "platform": platform, "description": description,
                "max_players": max_players, "scheduled_at": scheduled_at or ""}
        return templates.TemplateResponse(
            "posts/create.html",
            {"request": request, "platforms": VALID_PLATFORMS, "form": form,
             "errors": errors, "current_user": current_user},
        )

    from datetime import datetime
    sched = None
    if scheduled_at:
        try:
            sched = datetime.fromisoformat(scheduled_at)
        except ValueError:
            pass

    post = Post(
        author_id=current_user.id,
        game=game,
        platform=",".join(platform),
        description=description,
        max_players=max_players,
        scheduled_at=sched,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    flash(request, "LFG post created!", "success")
    return RedirectResponse(url=f"/posts/{post.id}", status_code=303)


@router.get("/{post_id}")
def post_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        flash(request, "Post not found.", "danger")
        return RedirectResponse(url="/posts", status_code=303)

    accepted_count = _accepted_count(db, post_id)
    members = (
        db.query(Membership)
        .filter_by(post_id=post_id, status="accepted")
        .all()
    )
    membership = None
    if current_user:
        membership = (
            db.query(Membership)
            .filter_by(user_id=current_user.id, post_id=post_id)
            .first()
        )
    pending_count = (
        db.query(Membership).filter_by(post_id=post_id, status="pending").count()
    )

    return templates.TemplateResponse(
        "posts/detail.html",
        {
            "request": request,
            "post": post,
            "accepted_count": accepted_count,
            "members": members,
            "membership": membership,
            "pending_count": pending_count,
            "current_user": current_user,
        },
    )


@router.get("/{post_id}/edit")
def edit_post_form(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not found or not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)
    return templates.TemplateResponse(
        "posts/edit.html",
        {"request": request, "post": post, "platforms": VALID_PLATFORMS, "current_user": current_user},
    )


@router.post("/{post_id}/edit")
def edit_post(
    request: Request,
    post_id: int,
    game: str = Form(...),
    platform: list[str] = Form(...),
    description: str = Form(...),
    max_players: int = Form(...),
    scheduled_at: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not found or not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)

    if profanity.contains_profanity(description):
        flash(request, "Description contains inappropriate language.", "danger")
        return RedirectResponse(url=f"/posts/{post_id}/edit", status_code=303)

    from datetime import datetime
    sched = None
    if scheduled_at:
        try:
            sched = datetime.fromisoformat(scheduled_at)
        except ValueError:
            pass

    post.game = game
    post.platform = ",".join(platform)
    post.description = description
    post.max_players = max_players
    post.scheduled_at = sched
    db.commit()
    flash(request, "Post updated.", "success")
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{post_id}/delete")
def delete_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id != current_user.id:
        flash(request, "Not found or not authorized.", "danger")
        return RedirectResponse(url="/posts", status_code=303)
    db.delete(post)
    db.commit()
    flash(request, "Post deleted.", "info")
    return RedirectResponse(url="/posts", status_code=303)
