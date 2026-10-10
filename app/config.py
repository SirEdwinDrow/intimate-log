import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{self.data_dir / 'app.db'}")
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", str(self.data_dir / "uploads"))).resolve()
        self.secret_key = os.getenv("SECRET_KEY", "dev-insecure-change-me")
        # После регистрации первого пользователя можно закрыть регистрацию
        self.allow_registration = os.getenv("ALLOW_REGISTRATION", "true").lower() in ("1", "true", "yes")
        self.max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
        self.https_only = os.getenv("HTTPS_ONLY", "false").lower() in ("1", "true", "yes")


settings = Settings()
