import random
import re
from typing import Optional


WAIT_KEYWORDS = [
    "wait", "cooldown", "try again", "come back", "timer", "remaining", "hold on",
    "через", "подождите", "зачекайте", "кулдаун", "попробуйте позже", "попробуйте через",
    "следующая карта", "следующий ролл", "следующий дроп", "вы сможете", "вы можете",
    "ви зможете", "ви можете"
]


def is_wait_message(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in WAIT_KEYWORDS)


def parse_cooldown_seconds(text: str) -> Optional[int]:
    if not text:
        return None

    cleaned = text.replace("\xa0", " ").strip()

    # 1. Digital format (e.g. 01:49:19 or 49:19)
    digital_match = re.search(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b", cleaned)
    if digital_match:
        h_str, m_str, s_str = digital_match.groups()
        if h_str is not None:
            total = int(h_str) * 3600 + int(m_str) * 60 + int(s_str)
            if total > 0:
                return total
        else:
            total = int(m_str) * 60 + int(s_str)
            if total > 0:
                return total

    # 2. Text components (days, hours, minutes, seconds)
    # Uses negative lookahead (?!\w) to support 1ч, 1ч., 1 ч, 1час, 49мин, 19сек cleanly
    total_seconds = 0
    found_any = False

    d_match = re.search(r"(\d+)\s*(?:дней|дня|день|днів|дні|days?|d|д)(?!\w)", cleaned, re.IGNORECASE)
    if d_match:
        total_seconds += int(d_match.group(1)) * 86400
        found_any = True

    h_match = re.search(r"(\d+)\s*(?:часов|часа|час|годин|години|година|hours?|hrs?|ч|г|h)(?!\w)", cleaned, re.IGNORECASE)
    if h_match:
        total_seconds += int(h_match.group(1)) * 3600
        found_any = True

    m_match = re.search(r"(\d+)\s*(?:минуты|минут|минута|хвилини|хвилин|хвилина|minutes?|mins?|мин|хв|м|m)(?!\w)", cleaned, re.IGNORECASE)
    if m_match:
        total_seconds += int(m_match.group(1)) * 60
        found_any = True

    s_match = re.search(r"(\d+)\s*(?:секунды|секунд|секунда|секунди|seconds?|secs?|сек|с|s)(?!\w)", cleaned, re.IGNORECASE)
    if s_match:
        total_seconds += int(s_match.group(1))
        found_any = True

    if found_any and total_seconds > 0:
        return total_seconds

    # 3. Fallback: single number after wait keyword (e.g. "через 15", meaning minutes)
    if is_wait_message(cleaned):
        num_match = re.search(r"(?:через|in|wait|зачекайте|подождите)\s*(\d+)", cleaned, re.IGNORECASE)
        if num_match:
            return int(num_match.group(1)) * 60

    return None


def calculate_wait_time(raw_seconds: int, min_jitter: int = 3, max_jitter: int = 15, fixed_jitter: Optional[int] = None) -> int:
    if raw_seconds <= 0:
        return 0
    if fixed_jitter is not None:
        jitter = max(0, fixed_jitter)
    else:
        jitter = random.randint(min_jitter, max_jitter)
    return raw_seconds + jitter


def format_countdown(seconds: Optional[int]) -> str:
    if seconds is None or seconds <= 0:
        return "00:00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_duration_friendly(seconds: Optional[int], lang: str = "en") -> str:
    if seconds is None or seconds <= 0:
        return "0s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    parts = []
    if lang == "ua":
        if h > 0: parts.append(f"{h} год")
        if m > 0: parts.append(f"{m} хв")
        if s > 0 or not parts: parts.append(f"{s} с")
    elif lang == "ru":
        if h > 0: parts.append(f"{h} ч")
        if m > 0: parts.append(f"{m} мин")
        if s > 0 or not parts: parts.append(f"{s} с")
    else:
        if h > 0: parts.append(f"{h}h")
        if m > 0: parts.append(f"{m}m")
        if s > 0 or not parts: parts.append(f"{s}s")
        
    return " ".join(parts)
