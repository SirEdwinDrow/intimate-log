<div align="center">

# IntimateLog

**A private, self-hosted diary for your love life — with ratings, spicy flags and a leaderboard.**
**Because your memory deserves a database, not a vibe.**

[![CI](https://github.com/SirEdwinDrow/intimate-log/actions/workflows/ci.yml/badge.svg)](https://github.com/SirEdwinDrow/intimate-log/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-server--rendered-009688)
![SQLite](https://img.shields.io/badge/SQLite-one%20file-lightgrey)
![18+](https://img.shields.io/badge/age-18%2B-e0457b)

**English** · [Русский](README.ru.md)

<img src="docs/screenshots/leaderboard.png" alt="Leaderboard" width="820">

</div>

---

## What is this?

You had a night. Then another one. Then someone asked "so who was the best?" and you said "uhh…" like a peasant.

**Intimate Log** fixes that. It is a tiny web app you run on your own machine (or a Raspberry Pi under your bed — we don't judge) where you:

1. **Create a partner card** — name, nickname, age, when you met, how many times, a description and a photo.
2. **Rate them** on 10 carefully engineered, peer-reviewed-by-nobody criteria.
3. **Slap on flags** — spicy ones, green ones, red ones.
4. **Watch them appear** in the **catalog** and on the **leaderboard**, complete with a podium, because life is a competition and so is this.

Everything stays **yours**: one account sees only its own data, photos never go public, and metadata is stripped before saving. This is a diary, not a dating site, not a social network, and definitely not a group chat screenshot.

## Features

| | |
|---|---|
| **Partner cards** | Name, nickname, age (18+ only, the app enforces it), date met, times counter, free-form description, photo |
| **10 weighted criteria** | Scores from 1 to 10, any of them can be skipped. Weighted average → final score → tier **S / A / B / C / D** |
| **Spicy flags** | 20 presets out of the box plus your own, created right from the card form |
| **Leaderboard** | Top-3 podium (gold, silver, bronze), full ranking table, "best in category" for each criterion, totals and average |
| **Catalog** | Search by name, nickname and description, filter by flag, sort by newest, score, name or times |
| **Photo privacy** | EXIF and GPS tags are wiped, image is resized to 1600 px, served only to the logged-in owner |
| **JSON export** | Download all your data. For backups. Or for your memoirs |
| **Mobile-friendly** | Looks fine on a phone, which is where, let's be honest, you'll be filling it in |
| **Dark theme** | The only theme. Some things are better in the dark |

<details>
<summary><b>More screenshots</b></summary>

| Catalog | Partner profile |
|---|---|
| <img src="docs/screenshots/catalog.png" width="400"> | <img src="docs/screenshots/profile.png" width="400"> |

| Rating form | Mobile |
|---|---|
| <img src="docs/screenshots/form.png" width="400"> | <img src="docs/screenshots/mobile.png" width="200"> |

Placeholder photos are solid colors. Your real ones will be more interesting. Probably.

</details>

## The rating system

Ten criteria, each with a weight. Chemistry matters more than stamina — that's science (citation needed).

| Criterion | Weight | What it means |
|---|:---:|---|
| Chemistry | **1.5** | Were there sparks, or just static electricity from the carpet? |
| Passion | 1.3 | Energy, desire, actually being there |
| Attentiveness | 1.3 | Did they care about *your* good time too? |
| Technique | 1.2 | Hands, lips, rhythm. Skill issue or skill flex |
| Comfort & communication | 1.2 | Easy to talk about wishes and boundaries |
| Kissing | 1.0 | A separate art form, deserves its own row |
| Creativity | 1.0 | Open to new things, or strictly the classics |
| Attraction | 1.0 | Looks, smell, voice — whatever does it for you |
| Stamina | 0.9 | Pace and duration. A marathon or a sprint |
| Afterwards | 0.8 | Cuddles, talks, the vibe after the credits roll |

**Final score** = weighted average of the criteria you filled in. Skipped ones don't drag the score down.

| Tier | Score | Translation |
|:---:|:---:|---|
| **S** | ≥ 9.0 | Legendary. Tell no one. Or everyone |
| **A** | ≥ 8.0 | Excellent, would recommend (to yourself) |
| **B** | ≥ 6.5 | Solid. Good times |
| **C** | ≥ 5.0 | It happened |
| **D** | < 5.0 | Character development |

Want different criteria or weights? Edit `app/scoring.py`. It's one list. You're a developer, you've got this.

## Flags

Four colors of flags, 20 presets out of the box (UI labels are in Russian):

- **Spicy** — "On fire", "Loves experiments", "Loud", "Dominant", "Submissive", "Role play", "Marathon runner", "Insatiable", "Morning person", "Gentle", "Scratches", "Lingerie on point"
- **Green** — "Want a repeat", "Green flag", "Talks about desires"
- **Red** — "Red flag", "Never again"
- **Neutral** — "Ex", "One night", "Relationship"

Add your own on the **Flags** page or right in the card form. Tags are per-account, so your weird ones stay your weird ones.

## Quick start

### Option A — Docker (recommended for servers and Raspberry Pi)

```bash
git clone https://github.com/SirEdwinDrow/intimate-log.git
cd intimate-log
cp .env.example .env
# put a real secret in .env:
python -c "import secrets;print(secrets.token_urlsafe(48))"
docker compose up -d --build
```

Open **http://127.0.0.1:8000**, register, then set `ALLOW_REGISTRATION=false` in `.env` and run `docker compose up -d` again. Now nobody else can sign up. Not even your ex.

### Option B — Windows without Docker

You need a **regular** Python 3.10–3.14 from [python.org](https://www.python.org/downloads/).

> **Heads-up:** the *free-threaded* build (`3.13t`) won't work — there are no prebuilt packages for it and pip will try to compile Pillow from scratch, and fail spectacularly. The script below detects this and picks the right Python for you.

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

The script finds a suitable Python, creates `.venv`, installs dependencies, generates a persistent `SECRET_KEY` into `.secret_key` and starts the server at **http://127.0.0.1:8000**.

### Option C — Linux / macOS, manually

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # + requirements-heif.txt for iPhone HEIC photos
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Configuration

All settings are environment variables (or `.env` for Docker).

| Variable | Default | What it does |
|---|---|---|
| `SECRET_KEY` | `dev-insecure-change-me` | Signs session cookies. **Change it.** Seriously |
| `ALLOW_REGISTRATION` | `true` | Set to `false` after creating your account. The first user can always register |
| `HTTPS_ONLY` | `false` | Set to `true` behind HTTPS (tunnel / reverse proxy) — cookies become `Secure` |
| `MAX_UPLOAD_MB` | `10` | Max photo size |
| `DATA_DIR` | `./data` | Where the database and photos live |
| `DATABASE_URL` | `sqlite:///<DATA_DIR>/app.db` | Any SQLAlchemy URL if SQLite feels too humble |
| `UPLOAD_DIR` | `<DATA_DIR>/uploads` | Photo storage |

## Exposing it to the internet (HTTPS via Tuna)

By default the app listens on `127.0.0.1` only. To open it from your phone outside of home, use a tunnel, for example [Tuna](https://tuna.am/docs/tunnels/http/):

```powershell
winget install --id yuccastream.tuna
tuna config save-token <YOUR_TOKEN>

# window 1 — the app
$env:HTTPS_ONLY = "true"
$env:ALLOW_REGISTRATION = "false"
powershell -ExecutionPolicy Bypass -File .\run.ps1

# window 2 — the tunnel
tuna http 8000 --subdomain=<your-free-subdomain> --https-redirect --inspect=false
```

| Address | Flag | Plan |
|---|---|---|
| `brave-otter-4821.ru.tuna.am` (random but permanent) | `--subdomain=brave-otter-4821` | free |
| `yourname.ru.tuna.am` (your choice) | `--subdomain=yourname` | subscription |
| `log.your-domain.com` (your own domain) | `--domain=log.your-domain.com` | subscription + a domain you actually own |

> **`Domain does not exist`?** You can't just make up a domain like `intim.log.ru` — you have to own it, add it in the Tuna dashboard and confirm it via DNS. The internet is not a wish-granting machine.

`--inspect=false` turns off Tuna's local request inspector, which would otherwise happily log your login password. Recommended.

## Privacy and security

This app holds the most sensitive data imaginable, so it is built paranoid:

- **Account isolation** — every query is scoped to the owner. User A can't see, edit, delete or even view a photo of User B's cards. There are tests for that
- **Private photos** — no public static folder. Photos are served through an endpoint that checks ownership
- **Metadata wipe** — EXIF, GPS coordinates and camera model are stripped on upload. Your bedroom's coordinates stay off the record
- **Passwords** — PBKDF2-SHA256, 390,000 iterations, random salt
- **CSRF tokens** on every form, `SameSite=Lax` session cookie, optional `Secure` flag
- **`noindex, nofollow`** — search engines are politely asked to look away
- **Docker** runs as a non-root user and binds to `127.0.0.1` only
- **Path traversal** attempts on photo URLs return a polite 404

**Backups:** everything lives in the `data/` folder (one SQLite file + photos). Copy it somewhere safe. Encrypted somewhere, ideally.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

18 tests cover: auth, CSRF, validation (including the 18+ check), full card lifecycle, leaderboard ordering, catalog search/filter/sort, flags CRUD, photo metadata stripping, account isolation, path traversal and closed registration.

CI on every push runs:
- **Linux** — tests
- **Windows** — install without a compiler, tests, `run.ps1` syntax check, server smoke test
- **Docker** — image build plus a container smoke test

## Project structure

```
app/
  main.py          routes: auth, cards, catalog, leaderboard, flags, export
  db.py            SQLAlchemy models: User, Partner, Score, Flag
  scoring.py       criteria, weights, tiers, preset flags  ← tweak me
  images.py        photo validation, EXIF stripping, resize
  security.py      password hashing, CSRF
  templates/       Jinja2 HTML
  static/style.css the whole design in one file
tests/             pytest suite
run.ps1            one-click Windows launcher
Dockerfile, docker-compose.yml
```

## Routes

| Method | Path | What |
|---|---|---|
| GET | `/leaderboard` | The podium of glory |
| GET | `/catalog?q=&flag=&sort=` | Everyone, searchable |
| GET/POST | `/partners/new`, `/partners` | Create a card |
| GET | `/partners/{id}` | Profile with score bars |
| GET/POST | `/partners/{id}/edit` | Edit |
| POST | `/partners/{id}/delete` | Delete (with photo) |
| GET/POST | `/flags` | Manage flags |
| GET | `/export` | JSON dump of your data |
| GET | `/healthz` | `{"status": "ok"}` — the app is alive, unlike some relationships |

## FAQ

**Is this ethical?**
It's a private diary. People have kept those for centuries, we just added a weighted average. Keep it private, don't share other people's data or photos without consent, and be nice.

**Can my partner see their score?**
Only if you show them. Which we do not recommend unless they're an S tier.

**Why is "Afterwards" weighted the lowest?**
Open an issue. Or a PR. Or a therapy session.

**Can I add guys / non-binary partners?**
Of course. The cards are for anyone; the name field doesn't care.

**Is there an API?**
There's `/export`. Anything more and it starts feeling like a business plan.

**I forgot my password.**
There's no reset — no email, no data leaks. Stop the app and delete `data/app.db` to start over (yes, losing everything). Or don't forget your password.

## License

Private project. All rights reserved. Use responsibly, 18+ only.

<div align="center"><sub>Built with FastAPI, SQLite and a questionable amount of self-reflection.</sub></div>
