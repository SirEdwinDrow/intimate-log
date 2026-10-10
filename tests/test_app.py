import io
import re

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from tests.conftest import csrf_of, make_jpeg, register


def create_partner(c, name="Катя", scores=None, flags=(), photo=None, **extra):
    token = csrf_of(c, "/partners/new")
    data = {"csrf": token, "name": name, "times": "3", **extra}
    for k, v in (scores or {}).items():
        data[f"score_{k}"] = str(v)
    if flags:
        data["flags"] = [str(f) for f in flags]
    files = {"photo": ("p.jpg", photo, "image/jpeg")} if photo else None
    return c.post("/partners", data=data, files=files, follow_redirects=False)


def flag_ids(c):
    html = c.get("/partners/new").text
    return dict((n, int(i)) for i, n in re.findall(r'name="flags" value="(\d+)"[^>]*>([^<]+)</label>', html))


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_requires_login(client):
    for url in ("/leaderboard", "/catalog", "/partners/new", "/flags", "/export"):
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"


def test_register_login_logout(client):
    assert register(client).status_code == 303
    assert "Лидерборд" in client.get("/leaderboard").text
    token = csrf_of(client, "/leaderboard")
    client.post("/logout", data={"csrf": token})
    assert client.get("/leaderboard", follow_redirects=False).status_code == 303
    token = csrf_of(client, "/login")
    bad = client.post("/login", data={"csrf": token, "username": "alex", "password": "wrong-pass"})
    assert bad.status_code == 400
    ok = client.post("/login", data={"csrf": token, "username": "alex", "password": "supersecret"},
                     follow_redirects=False)
    assert ok.status_code == 303


def test_register_validation(client):
    assert register(client, "ab", "supersecret").status_code == 400
    assert register(client, "alex", "short").status_code == 400
    assert register(client, "alex", "supersecret").status_code == 303


def test_csrf_enforced(auth_client):
    r = auth_client.post("/partners", data={"csrf": "nope", "name": "X"})
    assert r.status_code == 400


def test_preset_flags_seeded(auth_client):
    ids = flag_ids(auth_client)
    assert "Огонь" in ids and "Red flag" in ids and len(ids) >= 15


def test_full_flow_create_show_catalog_leaderboard(auth_client):
    c = auth_client
    ids = flag_ids(c)
    r = create_partner(c, "Катя", {"chemistry": 9, "passion": 10, "technique": 8},
                       flags=[ids["Огонь"], ids["Хочу повторить"]], photo=make_jpeg(),
                       nickname="Котик", age="24", met_on="2026-05-01", description="Познакомились на концерте")
    assert r.status_code == 303
    url = r.headers["location"]
    page = c.get(url).text
    assert "Катя" in page and "Котик" in page and "Огонь" in page and "#1 в лидерборде" in page
    photo_url = re.search(r'src="(/photos/[0-9a-f]+\.jpg)"', page).group(1)
    assert c.get(photo_url).headers["content-type"] == "image/jpeg"

    create_partner(c, "Лена", {"chemistry": 6, "passion": 5})
    create_partner(c, "Без оценки")

    board = c.get("/leaderboard").text
    assert board.index("Катя") < board.index("Лена")
    assert ">Без оценки<" not in board  # без оценок нет в лидерборде
    assert "Лучшие по критериям" in board

    cat = c.get("/catalog").text
    assert all(n in cat for n in ("Катя", "Лена", "Без оценки"))
    assert "Лена" not in c.get(f"/catalog?flag={ids['Огонь']}").text
    assert "Катя" in c.get("/catalog?q=концерт").text
    sorted_ = c.get("/catalog?sort=score").text
    assert sorted_.index("Катя") < sorted_.index("Лена") < sorted_.index("Без оценки")


def test_edit_and_delete(auth_client, cfg):
    c = auth_client
    r = create_partner(c, "Маша", {"chemistry": 5}, photo=make_jpeg())
    pid = int(r.headers["location"].rsplit("/", 1)[1])
    assert len(list(cfg.upload_dir.iterdir())) == 1

    token = csrf_of(c, f"/partners/{pid}/edit")
    r = c.post(f"/partners/{pid}/edit", data={"csrf": token, "name": "Маша Н.", "times": "5",
                                             "score_chemistry": "10", "score_passion": "10",
                                             "new_flag": "Танцует стриптиз"}, follow_redirects=False)
    assert r.status_code == 303
    page = c.get(f"/partners/{pid}").text
    assert "Маша Н." in page and "Танцует стриптиз" in page and "10.0" in page

    token = csrf_of(c, f"/partners/{pid}")
    c.post(f"/partners/{pid}/delete", data={"csrf": token})
    assert c.get(f"/partners/{pid}").status_code == 404
    assert list(cfg.upload_dir.iterdir()) == []  # фото удалено с диска


def test_validation_errors(auth_client):
    assert create_partner(auth_client, "").status_code == 400
    assert create_partner(auth_client, "Юная", age="16").status_code == 400
    assert create_partner(auth_client, "Фейк", photo=b"not an image").status_code == 400


def test_photo_metadata_stripped(auth_client, cfg):
    r = create_partner(auth_client, "Exif", photo=make_jpeg((3000, 2000), exif_gps=True))
    assert r.status_code == 303
    f = next(cfg.upload_dir.iterdir())
    img = Image.open(f)
    assert max(img.size) <= 1600
    assert len(img.getexif()) == 0


def test_isolation_between_users(app):
    with TestClient(app) as a, TestClient(app) as b:
        register(a, "alice", "supersecret")
        register(b, "bob__", "supersecret")
        r = create_partner(a, "Секрет", {"chemistry": 9}, photo=make_jpeg())
        pid = int(r.headers["location"].rsplit("/", 1)[1])
        photo_url = re.search(r'src="(/photos/[^"]+)"', a.get(f"/partners/{pid}").text).group(1)

        assert b.get(f"/partners/{pid}").status_code == 404
        assert b.get(f"/partners/{pid}/edit").status_code == 404
        assert b.get(photo_url).status_code == 404
        assert "Секрет" not in b.get("/catalog").text
        assert "Секрет" not in b.get("/leaderboard").text
        token = csrf_of(b, "/catalog")
        assert b.post(f"/partners/{pid}/delete", data={"csrf": token}).status_code == 404
        # чужой флаг нельзя прицепить
        alice_flag = flag_ids(a)["Огонь"]
        r = create_partner(b, "Моя", flags=[alice_flag])
        page = b.get(r.headers["location"]).text
        assert "Огонь" not in page


def test_path_traversal_photo(auth_client):
    assert auth_client.get("/photos/..%2F..%2Fapp.db").status_code == 404


def test_flags_crud(auth_client):
    c = auth_client
    token = csrf_of(c, "/flags")
    c.post("/flags", data={"csrf": token, "name": "Любит кожу", "color": "spicy"})
    assert "Любит кожу" in c.get("/flags").text
    fid = flag_ids(c)["Любит кожу"]
    c.post(f"/flags/{fid}/delete", data={"csrf": token})
    assert "Любит кожу" not in c.get("/flags").text


def test_export(auth_client):
    create_partner(auth_client, "Оля", {"chemistry": 7})
    data = auth_client.get("/export").json()
    assert data["partners"][0]["name"] == "Оля"
    assert data["partners"][0]["overall"] == 7.0


def test_registration_can_be_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    from app.config import Settings
    app = create_app(Settings())
    with TestClient(app) as c:
        assert register(c, "owner", "supersecret").status_code == 303  # первый пользователь разрешён
    with TestClient(app) as c2:
        assert c2.get("/register").status_code == 403
