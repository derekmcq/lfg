from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import engine, Base
from app.flash import get_flashed_messages
from app.csrf import CSRFMiddleware, csrf_input
from app.routers.notifications import get_unread_count

# Import models so Base.metadata knows about them before create_all
import app.models  # noqa: F401

from app.routers import auth, posts, memberships, dashboard, notifications

app = FastAPI(title="LFG")

# SessionMiddleware must be added last (outermost) so session is populated before CSRF runs
app.add_middleware(CSRFMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(memberships.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)

# Inject globals into every router's Jinja2 environment
for mod in (auth, posts, memberships, dashboard, notifications):
    mod.templates.env.globals["get_flashed_messages"] = get_flashed_messages
    mod.templates.env.globals["csrf_input"] = csrf_input
    mod.templates.env.globals["get_unread_count"] = get_unread_count


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return RedirectResponse(url="/posts", status_code=303)
