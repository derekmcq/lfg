# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LFG ("Looking For Group") — a FastAPI web app where users post and join gaming groups. Stack: FastAPI + PostgreSQL + Jinja2 + Bootstrap 5.

## Commands

```bash
# Activate virtual environment (required each new terminal)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server (auto-reloads on file changes)
uvicorn app.main:app --reload

# Database tables are created automatically on startup via create_all
```

## Architecture

**Entry point:** `app/main.py` — creates the FastAPI app, registers `SessionMiddleware`, includes all routers, and injects `get_flashed_messages` into every router's Jinja2 template environment via `mod.templates.env.globals`.

**Database:** SQLAlchemy ORM with a `DeclarativeBase` in `app/database.py`. Models live in `app/models/`. `Base.metadata.create_all` runs on startup — no migrations, schema changes require manual table drops in dev.

**Session-based auth:** User identity is stored in `request.session["user_id"]` and `request.session["username"]` (Starlette `SessionMiddleware`). `get_current_user` in `app/dependencies.py` looks up the user from the session on every request. There are no JWT tokens or OAuth flows.

**Flash messages:** Implemented manually in `app/flash.py` using `request.session["_flashes"]`. Messages are popped on read. `get_flashed_messages` is registered as a Jinja2 global so templates call it as `get_flashed_messages(request)`.

**Templates:** Each router module has its own `templates = Jinja2Templates(...)` instance at module level. `main.py` patches all of them with shared globals after import. Templates use `request.session.username` (not a standalone `session` variable).

**Membership model:** Three statuses — `pending`, `accepted`, `denied`. A `UniqueConstraint("user_id", "post_id")` enforces one row per user per post; re-requests after denial update the existing row rather than inserting a new one.

**Member counts:** The post author is never in the `memberships` table but occupies one slot. All member count displays and capacity checks add `+1` to account for the author.

**All POST routes use Post-Redirect-Get** (redirect with 303 after mutations).

## Key files

| File | Purpose |
|------|---------|
| `app/main.py` | App factory, middleware, router wiring, Jinja2 global injection |
| `app/models/membership.py` | Core join-request logic lives here (statuses, constraints) |
| `app/routers/memberships.py` | All join/leave/accept/deny endpoints |
| `app/routers/posts.py` | CRUD + `ilike` filtering |
| `app/schemas/post.py` | `VALID_PLATFORMS` list used by both router and templates |
| `app/flash.py` | Flash message implementation |
