import io
import re

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("UPLOAD_DIR", raising=False)
    return Settings()


@pytest.fixture
def app(cfg):
    return create_app(cfg)


def csrf_of(client: TestClient, url: str = "/login") -> str:
    html = client.get(url).text
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m, f"no csrf on {url}"
    return m.group(1)


def register(client: TestClient, username="alex", password="supersecret"):
    token = csrf_of(client, "/register")
    return client.post("/register", data={"csrf": token, "username": username, "password": password},
                       follow_redirects=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(app):
    with TestClient(app) as c:
        r = register(c)
        assert r.status_code == 303
        yield c


def make_jpeg(size=(800, 600), color=(200, 50, 90), exif_gps=False) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    if exif_gps:
        exif = Image.Exif()
        exif[0x010F] = "SpyCam"  # Make
        img.save(buf, "JPEG", exif=exif.tobytes())
    else:
        img.save(buf, "JPEG")
    return buf.getvalue()
