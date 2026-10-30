import re
from typing import Optional, Dict, Any


DROP_PATTERNS = [
    re.compile(
        r"(?:@\w+\s+)?(?:.+?you\s+got\s+a\s+phone!|.+?вы\s+выбили\s+телефон!|.+?ви\s+вибили\s+телефон!)\s*"
        r"\n\s*(?:[📱\s*]*)([^\n\r]+)\s*"
        r"\n\s*([^|\n\r]+?)\s*\|\s*(?:цена|ціна|price):\s*([\d\s.,]+?)\s*(?:очков|очки|pts|points)(?:\b|$)",
        re.IGNORECASE
    ),
    re.compile(
        r"(?:@\w+\s+)?(?:.+?you\s+got\s+a\s+phone!|.+?вы\s+выбили\s+телефон!|.+?ви\s+вибили\s+телефон!)\s*"
        r"\n\s*(?:[📱\s*]*)([^\n\r]+)\s*"
        r"\n\s*([^|\n\r]+?)\s*\|\s*(?:цена|ціна|price):\s*([\d\s.,]+)",
        re.IGNORECASE
    ),
    re.compile(
        r"(?:📱\s*)([^\n\r]+)\s*"
        r"\n\s*([^|\n\r]+?)\s*\|\s*(?:цена|ціна|price):\s*([\d\s.,]+)",
        re.IGNORECASE
    ),
    re.compile(
        r"[*_📱\s]*([a-zA-Z0-9\s\+\-\.\/]{3,50})[*_\s]*\n\s*"
        r"([^|\n\r]+?)\s*\|\s*(?:цена|ціна|price):\s*([\d\s.,]+)",
        re.IGNORECASE
    )
]


def clean_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    s = price_str.strip().replace(" ", "").replace("\xa0", "").replace("'", "")
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_drop_message(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    cleaned_text = text.replace("\xa0", " ").strip()

    for pattern in DROP_PATTERNS:
        match = pattern.search(cleaned_text)
        if match:
            raw_device = match.group(1).strip().strip("*_` #")
            raw_rarity = match.group(2).strip().strip("*_` ")
            raw_price_str = match.group(3).strip()
            price_val = clean_price(raw_price_str)

            if raw_device and raw_rarity and price_val > 0:
                return {
                    "device_name": raw_device,
                    "rarity": raw_rarity,
                    "price": price_val,
                    "raw_price_str": raw_price_str
                }

    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if "цена:" in line_lower or "ціна:" in line_lower or "price:" in line_lower:
            parts = line.split("|")
            if len(parts) >= 2:
                rarity_candidate = parts[0].strip().strip("*_` ")
                price_match = re.search(r'(?:цена|ціна|price):\s*([\d\s.,]+)', parts[1], re.IGNORECASE)
                price_candidate = clean_price(price_match.group(1)) if price_match else 0.0
                if i > 0:
                    device_line = lines[i - 1].replace("📱", "").strip().strip("*_` ")
                    if device_line:
                        return {
                            "device_name": device_line,
                            "rarity": rarity_candidate,
                            "price": price_candidate,
                            "raw_price_str": str(price_candidate)
                        }
    return None
