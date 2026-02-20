# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LFG ("Looking For Group") — a FastAPI web app where users post and join gaming groups. Stack: FastAPI + PostgreSQL + Jinja2 + Bootstrap 5 (dark theme).

## Commands

```bash
# Activate virtual environment (required each new terminal)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server (auto-reloads on file changes)
uvicorn app.main:app --reload

# Database tables are created automatically on startup via create_all
# No migrations — schema changes require manual ALTER TABLE or dropping/recreating tables in psql:
#   psql -U lfguser -d lfg -h localhost (password: lfgpass)
```

## Architecture

**Entry point:** `app/main.py` — creates the FastAPI app, registers middleware, includes all routers, mounts static files at `/static`, and injects shared Jinja2 globals (`get_flashed_messages`, `csrf_input`, `get_unread_count`) into every router's template environment via `mod.templates.env.globals`.

**Database:** SQLAlchemy ORM with `DeclarativeBase` in `app/database.py`. Models in `app/models/`. `Base.metadata.create_all` runs on startup — no migrations.

**Session-based auth:** User identity stored in `request.session["user_id"]` and `request.session["username"]` (Starlette `SessionMiddleware`). `get_current_user` in `app/dependencies.py` looks up the user from the session on every request. No JWT or OAuth.

**CSRF protection:** `app/csrf.py` provides `CSRFMiddleware` that validates a `_csrf_token` form field against `request.session["_csrf_token"]` on all non-safe methods. `csrf_input(request)` helper generates the hidden input. Only validates `application/x-www-form-urlencoded` — JSON API endpoints (like `/api/*`) pass through without CSRF.

**Flash messages:** `app/flash.py` stores messages in `request.session["_flashes"]`, popped on read. Registered as a Jinja2 global.

**Templates:** Each router module has its own `Jinja2Templates` instance. `main.py` patches all of them with shared globals after import. The `api` router has no templates and is excluded from this loop. Templates access session via `request.session.username`.

**Middleware order:** SessionMiddleware (outermost) → CSRFMiddleware → Router. SessionMiddleware must be added last so the session is populated before CSRF runs.

**Membership model:** Three statuses — `pending`, `accepted`, `denied`. `UniqueConstraint("user_id", "post_id")` enforces one row per user per post; re-requests after denial update the existing row.

**Member counts:** The post author is never in the `memberships` table but occupies one slot. All displays and capacity checks add `+1` for the author.

**Multi-platform posts:** Platforms stored as comma-separated string in `Post.platform` (String(200)). `Post.platform_list` property splits into a list. `VALID_PLATFORMS` in `app/schemas/post.py` defines the canonical set: PC, PlayStation, Xbox, Nintendo Switch, Mobile, Other.

**IGDB integration:** `app/igdb.py` provides game search with cover images and platform data. OAuth token cached in-memory. `app/routers/api.py` exposes `GET /api/games/search?q=...` as a JSON endpoint. Frontend JS (`app/static/js/game-search.js`) implements typeahead with 300ms debounce, renders dropdown with covers, and auto-checks platform checkboxes on game selection. Config: `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` in `.env`.

**Validation:** Registration uses regex + profanity checks (`better-profanity`). Post descriptions also have profanity validation. Form errors render inline (re-render form with `errors` dict, not flash messages).

**All POST routes use Post-Redirect-Get** (redirect with 303 after mutations).

## Key files

| File | Purpose |
|------|---------|
| `app/main.py` | App factory, middleware, router wiring, static mount, Jinja2 global injection |
| `app/csrf.py` | CSRF middleware and `csrf_input` helper |
| `app/igdb.py` | IGDB API client: token caching, game search, platform mapping |
| `app/models/membership.py` | Join-request logic (statuses, unique constraint) |
| `app/routers/posts.py` | Post CRUD + filtering + profanity validation |
| `app/routers/memberships.py` | All join/leave/accept/deny endpoints |
| `app/routers/api.py` | JSON API endpoints (game search) |
| `app/schemas/post.py` | `VALID_PLATFORMS` list used by router, templates, and IGDB mapping |
| `app/static/js/game-search.js` | Client-side IGDB typeahead search |
| `app/templates/base.html` | Layout, navbar, dark theme styles, flash messages, JS includes |
