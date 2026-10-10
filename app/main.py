from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.datastructures import UploadFile
from starlette.middleware.sessions import SessionMiddleware

from . import scoring
from .config import Settings, settings as default_settings
from .db import Base, Flag, Partner, Score, User, make_engine, make_sessionmaker, partner_flags
from .images import ImageError, delete_photo, save_photo
from .security import check_csrf, get_csrf_token, hash_password, verify_password

BASE_DIR = Path(__file__).parent


class LoginRequired(Exception):
    pass


def create_app(cfg: Settings | None = None) -> FastAPI:
    cfg = cfg or default_settings
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(cfg.database_url)
    Base.metadata.create_all(engine)
    SessionLocal = make_sessionmaker(engine)

    app = FastAPI(title="Intimate Log", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.cfg = cfg
    app.state.engine = engine
    app.add_middleware(SessionMiddleware, secret_key=cfg.secret_key, same_site="lax",
                       https_only=cfg.https_only, max_age=60 * 60 * 24 * 14)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    templates.env.globals.update(CRITERIA=scoring.CRITERIA, tier=scoring.tier)

    # ---------- helpers ----------
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def current_user(request: Request, db: Session = Depends(get_db)) -> User:
        uid = request.session.get("uid")
        user = db.get(User, uid) if uid else None
        if not user:
            raise LoginRequired()
        return user

    def render(request: Request, name: str, ctx: dict | None = None, status: int = 200, user=None):
        ctx = dict(ctx or {})
        ctx.update(request=request, user=user, csrf=get_csrf_token(request.session),
                   flashes=request.session.pop("flashes", []))
        return templates.TemplateResponse(request, name, ctx, status_code=status)

    def flash(request: Request, msg: str, kind: str = "ok"):
        request.session.setdefault("flashes", []).append({"msg": msg, "kind": kind})

    async def form_checked(request: Request):
        form = await request.form()
        if not check_csrf(request.session, form.get("csrf")):
            raise HTTPException(400, "CSRF token invalid")
        return form

    def own_partner(db: Session, user: User, pid: int) -> Partner:
        p = db.scalar(select(Partner).where(Partner.id == pid, Partner.owner_id == user.id)
                      .options(selectinload(Partner.scores), selectinload(Partner.flags)))
        if not p:
            raise HTTPException(404, "Не найдено")
        return p

    def seed_flags(db: Session, user: User):
        for f in scoring.PRESET_FLAGS:
            db.add(Flag(owner_id=user.id, name=f.name, color=f.color))

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        return RedirectResponse("/login", status_code=303)

    # ---------- auth ----------
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/")
    def index(request: Request):
        return RedirectResponse("/leaderboard" if request.session.get("uid") else "/login", 303)

    def registration_open(db: Session) -> bool:
        return cfg.allow_registration or db.scalar(select(func.count(User.id))) == 0

    @app.get("/register", response_class=HTMLResponse)
    def register_page(request: Request, db: Session = Depends(get_db)):
        if not registration_open(db):
            return render(request, "auth.html", {"mode": "register", "closed": True}, 403)
        return render(request, "auth.html", {"mode": "register"})

    @app.post("/register")
    async def register(request: Request, db: Session = Depends(get_db)):
        form = await form_checked(request)
        if not registration_open(db):
            raise HTTPException(403, "Регистрация закрыта")
        username = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))
        error = None
        if not (3 <= len(username) <= 64) or not username.replace("_", "").replace(".", "").isalnum():
            error = "Логин: 3–64 символа, буквы, цифры, _ и ."
        elif len(password) < 8:
            error = "Пароль минимум 8 символов"
        elif db.scalar(select(User).where(User.username == username)):
            error = "Такой логин уже занят"
        if error:
            return render(request, "auth.html", {"mode": "register", "error": error, "username": username}, 400)
        user = User(username=username, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        seed_flags(db, user)
        db.commit()
        request.session.clear()
        request.session["uid"] = user.id
        flash(request, "Добро пожаловать. Создай первую карточку.")
        return RedirectResponse("/partners/new", 303)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, db: Session = Depends(get_db)):
        return render(request, "auth.html", {"mode": "login", "can_register": registration_open(db)})

    @app.post("/login")
    async def login(request: Request, db: Session = Depends(get_db)):
        form = await form_checked(request)
        username = str(form.get("username", "")).strip().lower()
        user = db.scalar(select(User).where(User.username == username))
        if not user or not verify_password(str(form.get("password", "")), user.password_hash):
            return render(request, "auth.html", {"mode": "login", "error": "Неверный логин или пароль",
                                                 "username": username, "can_register": registration_open(db)}, 400)
        request.session.clear()
        request.session["uid"] = user.id
        return RedirectResponse("/leaderboard", 303)

    @app.post("/logout")
    async def logout(request: Request):
        await form_checked(request)
        request.session.clear()
        return RedirectResponse("/login", 303)

    # ---------- catalog & leaderboard ----------
    @app.get("/catalog", response_class=HTMLResponse)
    def catalog(request: Request, q: str = "", flag: int | None = None, sort: str = "recent",
                user: User = Depends(current_user), db: Session = Depends(get_db)):
        stmt = (select(Partner).where(Partner.owner_id == user.id)
                .options(selectinload(Partner.flags)))
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Partner.name.ilike(like), Partner.nickname.ilike(like),
                                  Partner.description.ilike(like)))
        if flag:
            stmt = stmt.where(Partner.flags.any(Flag.id == flag))
        order = {
            "recent": [Partner.created_at.desc()],
            "score": [Partner.overall.desc().nulls_last(), Partner.name],
            "name": [Partner.name],
            "times": [Partner.times.desc(), Partner.name],
        }.get(sort, [Partner.created_at.desc()])
        partners = db.scalars(stmt.order_by(*order)).all()
        flags = db.scalars(select(Flag).where(Flag.owner_id == user.id).order_by(Flag.name)).all()
        return render(request, "catalog.html", {"partners": partners, "flags": flags, "q": q,
                                                "flag": flag, "sort": sort}, user=user)

    @app.get("/leaderboard", response_class=HTMLResponse)
    def leaderboard(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        partners = db.scalars(
            select(Partner).where(Partner.owner_id == user.id, Partner.overall.is_not(None))
            .options(selectinload(Partner.flags), selectinload(Partner.scores))
            .order_by(Partner.overall.desc(), Partner.times.desc(), Partner.name)
        ).all()
        best_by = []
        for c in scoring.CRITERIA:
            top = max(partners, key=lambda p: (p.score_map().get(c.key, 0), p.overall or 0), default=None)
            if top and top.score_map().get(c.key):
                best_by.append((c, top, top.score_map()[c.key]))
        total = db.scalar(select(func.count(Partner.id)).where(Partner.owner_id == user.id))
        avg = round(sum(p.overall for p in partners) / len(partners), 1) if partners else None
        return render(request, "leaderboard.html", {"partners": partners, "best_by": best_by,
                                                    "total": total, "avg": avg}, user=user)

    # ---------- partners CRUD ----------
    def partner_form_ctx(db: Session, user: User, partner: Partner | None, error: str | None = None):
        flags = db.scalars(select(Flag).where(Flag.owner_id == user.id).order_by(Flag.color, Flag.name)).all()
        return {"partner": partner, "flags": flags, "error": error,
                "scores": partner.score_map() if partner else {},
                "selected": {f.id for f in partner.flags} if partner else set()}

    async def apply_form(request: Request, db: Session, user: User, partner: Partner, form) -> str | None:
        name = str(form.get("name", "")).strip()
        if not name:
            return "Имя обязательно"
        partner.name = name[:80]
        partner.nickname = (str(form.get("nickname", "")).strip() or None)
        partner.description = str(form.get("description", "")).strip()[:5000]
        age = str(form.get("age", "")).strip()
        partner.age = int(age) if age.isdigit() and 18 <= int(age) <= 120 else None
        if age and partner.age is None:
            return "Возраст должен быть числом от 18"
        met = str(form.get("met_on", "")).strip()
        try:
            partner.met_on = date.fromisoformat(met) if met else None
        except ValueError:
            return "Неверная дата"
        times = str(form.get("times", "1")).strip()
        partner.times = max(1, min(100000, int(times))) if times.isdigit() else 1

        # оценки
        values = {c.key: scoring.clamp_score(form.get(f"score_{c.key}")) for c in scoring.CRITERIA}
        existing = {s.criterion: s for s in partner.scores}
        for key, val in values.items():
            if val is None:
                if key in existing:
                    partner.scores.remove(existing[key])
            elif key in existing:
                existing[key].value = val
            else:
                partner.scores.append(Score(criterion=key, value=val))
        partner.overall = scoring.overall_score(values)

        # флаги (только свои)
        ids = {int(x) for x in form.getlist("flags") if str(x).isdigit()}
        partner.flags = list(db.scalars(select(Flag).where(Flag.owner_id == user.id, Flag.id.in_(ids)))) if ids else []
        new_flag = str(form.get("new_flag", "")).strip()[:40]
        if new_flag:
            f = db.scalar(select(Flag).where(Flag.owner_id == user.id, Flag.name == new_flag))
            if not f:
                f = Flag(owner_id=user.id, name=new_flag, color="spicy")
                db.add(f)
            if f not in partner.flags:
                partner.flags.append(f)

        # фото
        photo = form.get("photo")
        if form.get("remove_photo") and partner.photo:
            delete_photo(partner.photo, cfg.upload_dir)
            partner.photo = None
        if isinstance(photo, UploadFile) and photo.filename:
            data = await photo.read()
            try:
                new_name = save_photo(data, cfg.upload_dir, cfg.max_upload_mb * 1024 * 1024)
            except ImageError as e:
                return str(e)
            delete_photo(partner.photo, cfg.upload_dir)
            partner.photo = new_name
        return None

    @app.get("/partners/new", response_class=HTMLResponse)
    def new_partner(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        return render(request, "partner_form.html", partner_form_ctx(db, user, None), user=user)

    @app.post("/partners")
    async def create_partner(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        form = await form_checked(request)
        partner = Partner(owner_id=user.id, scores=[], flags=[])
        error = await apply_form(request, db, user, partner, form)
        if error:
            db.rollback()
            return render(request, "partner_form.html", partner_form_ctx(db, user, None, error), 400, user)
        db.add(partner)
        db.commit()
        flash(request, f"Карточка «{partner.name}» создана")
        return RedirectResponse(f"/partners/{partner.id}", 303)

    @app.get("/partners/{pid}", response_class=HTMLResponse)
    def show_partner(pid: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        p = own_partner(db, user, pid)
        rank = None
        if p.overall is not None:
            rank = 1 + db.scalar(select(func.count(Partner.id)).where(
                Partner.owner_id == user.id, Partner.overall > p.overall))
        return render(request, "partner_show.html", {"p": p, "scores": p.score_map(), "rank": rank}, user=user)

    @app.get("/partners/{pid}/edit", response_class=HTMLResponse)
    def edit_partner(pid: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        p = own_partner(db, user, pid)
        return render(request, "partner_form.html", partner_form_ctx(db, user, p), user=user)

    @app.post("/partners/{pid}/edit")
    async def update_partner(pid: int, request: Request, user: User = Depends(current_user),
                             db: Session = Depends(get_db)):
        form = await form_checked(request)
        p = own_partner(db, user, pid)
        error = await apply_form(request, db, user, p, form)
        if error:
            db.rollback()
            p = own_partner(db, user, pid)
            return render(request, "partner_form.html", partner_form_ctx(db, user, p, error), 400, user)
        db.commit()
        flash(request, "Сохранено")
        return RedirectResponse(f"/partners/{p.id}", 303)

    @app.post("/partners/{pid}/delete")
    async def delete_partner(pid: int, request: Request, user: User = Depends(current_user),
                             db: Session = Depends(get_db)):
        await form_checked(request)
        p = own_partner(db, user, pid)
        delete_photo(p.photo, cfg.upload_dir)
        db.delete(p)
        db.commit()
        flash(request, "Карточка удалена")
        return RedirectResponse("/catalog", 303)

    @app.get("/photos/{name}")
    def photo(name: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
        owned = db.scalar(select(Partner.id).where(Partner.owner_id == user.id, Partner.photo == name))
        path = (cfg.upload_dir / name).resolve()
        if not owned or path.parent != cfg.upload_dir.resolve() or not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

    # ---------- flags ----------
    @app.get("/flags", response_class=HTMLResponse)
    def flags_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        rows = db.execute(
            select(Flag, func.count(partner_flags.c.partner_id))
            .outerjoin(partner_flags, Flag.id == partner_flags.c.flag_id)
            .where(Flag.owner_id == user.id).group_by(Flag.id).order_by(Flag.color, Flag.name)
        ).all()
        return render(request, "flags.html", {"rows": rows}, user=user)

    @app.post("/flags")
    async def create_flag(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        form = await form_checked(request)
        name = str(form.get("name", "")).strip()[:40]
        color = str(form.get("color", "spicy"))
        if color not in scoring.FLAG_COLORS:
            color = "spicy"
        if name and not db.scalar(select(Flag).where(Flag.owner_id == user.id, Flag.name == name)):
            db.add(Flag(owner_id=user.id, name=name, color=color))
            db.commit()
            flash(request, f"Флаг «{name}» добавлен")
        return RedirectResponse("/flags", 303)

    @app.post("/flags/{fid}/delete")
    async def delete_flag(fid: int, request: Request, user: User = Depends(current_user),
                          db: Session = Depends(get_db)):
        await form_checked(request)
        f = db.scalar(select(Flag).where(Flag.id == fid, Flag.owner_id == user.id))
        if not f:
            raise HTTPException(404)
        db.delete(f)
        db.commit()
        return RedirectResponse("/flags", 303)

    # ---------- export ----------
    @app.get("/export")
    def export(user: User = Depends(current_user), db: Session = Depends(get_db)):
        partners = db.scalars(select(Partner).where(Partner.owner_id == user.id)
                              .options(selectinload(Partner.scores), selectinload(Partner.flags))).all()
        data = [{
            "id": p.id, "name": p.name, "nickname": p.nickname, "age": p.age,
            "met_on": p.met_on.isoformat() if p.met_on else None, "times": p.times,
            "description": p.description, "overall": p.overall, "tier": scoring.tier(p.overall),
            "scores": p.score_map(), "flags": [f.name for f in p.flags],
        } for p in partners]
        return JSONResponse({"user": user.username, "partners": data},
                            headers={"Content-Disposition": "attachment; filename=export.json"})

    return app


app = create_app()
