import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

try:  # поддержка фото с iPhone
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:  # pragma: no cover
    pass

MAX_SIDE = 1600


class ImageError(ValueError):
    pass


def save_photo(data: bytes, upload_dir: Path, max_bytes: int) -> str:
    """Проверяет картинку, поворачивает по EXIF, удаляет метаданные (геолокацию и т.п.), сохраняет JPEG."""
    if not data:
        raise ImageError("Пустой файл")
    if len(data) > max_bytes:
        raise ImageError("Файл слишком большой")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ImageError("Это не похоже на изображение") from e
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(upload_dir / name, "JPEG", quality=86, optimize=True)  # без exif => метаданные стёрты
    return name


def delete_photo(name: str | None, upload_dir: Path) -> None:
    if not name:
        return
    p = (upload_dir / name).resolve()
    if p.parent == upload_dir.resolve() and p.exists():
        p.unlink()
