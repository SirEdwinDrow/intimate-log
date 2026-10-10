"""Критерии оценки и предустановленные флаги."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    key: str
    title: str
    hint: str
    weight: float


CRITERIA: list[Criterion] = [
    Criterion("chemistry", "Химия", "Насколько «искрило» между вами", 1.5),
    Criterion("passion", "Страсть", "Энергия, желание, вовлечённость", 1.3),
    Criterion("technique", "Техника", "Умения, чувство ритма, руки и губы", 1.2),
    Criterion("attentiveness", "Внимательность", "Забота о твоём удовольствии, чуткость", 1.3),
    Criterion("kissing", "Поцелуи", "Отдельный вид искусства", 1.0),
    Criterion("stamina", "Выносливость", "Темп и продолжительность", 0.9),
    Criterion("creativity", "Фантазия", "Открытость к экспериментам и новому", 1.0),
    Criterion("comfort", "Комфорт и общение", "Легко ли говорить о желаниях и границах", 1.2),
    Criterion("attraction", "Привлекательность", "Внешность, запах, голос — всё, что заводит", 1.0),
    Criterion("aftercare", "После", "Объятия, разговоры, атмосфера после", 0.8),
]
CRITERIA_KEYS = [c.key for c in CRITERIA]
SCORE_MIN, SCORE_MAX = 1, 10


@dataclass(frozen=True)
class PresetFlag:
    name: str
    color: str  # spicy | green | red | neutral


PRESET_FLAGS: list[PresetFlag] = [
    PresetFlag("Огонь", "spicy"),
    PresetFlag("Любит эксперименты", "spicy"),
    PresetFlag("Громкая", "spicy"),
    PresetFlag("Доминант", "spicy"),
    PresetFlag("Нижняя", "spicy"),
    PresetFlag("Ролевые игры", "spicy"),
    PresetFlag("Марафонец", "spicy"),
    PresetFlag("Ненасытная", "spicy"),
    PresetFlag("Утренняя", "spicy"),
    PresetFlag("Нежная", "spicy"),
    PresetFlag("Царапается", "spicy"),
    PresetFlag("Белье огонь", "spicy"),
    PresetFlag("Хочу повторить", "green"),
    PresetFlag("Green flag", "green"),
    PresetFlag("Говорит о желаниях", "green"),
    PresetFlag("Red flag", "red"),
    PresetFlag("Больше не повторю", "red"),
    PresetFlag("Бывшая", "neutral"),
    PresetFlag("Одна ночь", "neutral"),
    PresetFlag("Отношения", "neutral"),
]
FLAG_COLORS = {"spicy", "green", "red", "neutral"}


def clamp_score(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return max(SCORE_MIN, min(SCORE_MAX, v))


def overall_score(scores: dict[str, int | None]) -> float | None:
    """Взвешенное среднее по заполненным критериям, шкала 0–10, одна цифра после запятой."""
    total = weight = 0.0
    for c in CRITERIA:
        v = scores.get(c.key)
        if v is not None:
            total += v * c.weight
            weight += c.weight
    if weight == 0:
        return None
    return round(total / weight, 1)


def tier(score: float | None) -> str:
    if score is None:
        return "—"
    if score >= 9:
        return "S"
    if score >= 8:
        return "A"
    if score >= 6.5:
        return "B"
    if score >= 5:
        return "C"
    return "D"
