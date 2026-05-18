import re
import unicodedata
from config import NON_NUMERIC_PATTERNS


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    # Convert fullwidth characters to halfwidth
    result = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            result.append(" ")
        elif code in (0xFF08,):  # fullwidth (
            result.append("(")
        elif code in (0xFF09,):  # fullwidth )
            result.append(")")
        else:
            result.append(ch)
    return "".join(result).strip()


def make_match_key(name: str, brand: str, spec: str) -> str:
    parts = [normalize_text(name), normalize_text(brand), normalize_text(spec)]
    return "|||".join(p for p in parts if p)


def extract_number(raw: str) -> tuple:
    if not raw or not str(raw).strip():
        return (None, str(raw) if raw else "")
    s = str(raw).strip()

    # Check for non-numeric markers
    for pattern in NON_NUMERIC_PATTERNS:
        if pattern in s:
            return (None, s)

    # Try direct float conversion
    try:
        return (float(s), s)
    except ValueError:
        pass

    # Extract number from text like "各2", "一共18个", "各1", "200个"
    # Look for patterns like "各(\d+)" or just extract digits
    m = re.search(r"各\s*(\d+(?:\.\d+)?)", s)
    if m:
        return (float(m.group(1)), s)

    # "一共18个" pattern
    m = re.search(r"一共\s*(\d+(?:\.\d+)?)\s*个", s)
    if m:
        return (float(m.group(1)), s)

    # General: extract all digits/dots, prefer the first standalone number
    numbers = re.findall(r"\d+(?:\.\d+)?", s)
    if len(numbers) == 1:
        return (float(numbers[0]), s)

    # Multiple numbers found - ambiguous
    if numbers:
        return (None, s)

    return (None, s)


def is_summary_row(row_texts: list, keywords: list) -> bool:
    combined = "".join(str(t) for t in row_texts if t)
    for kw in keywords:
        if kw in combined:
            return True
    return False


def fuzzy_similarity(a: str, b: str) -> int:
    if not a and not b:
        return 100
    if not a or not b:
        return 0
    a, b = normalize_text(a), normalize_text(b)
    if a == b:
        return 100

    # Levenshtein distance
    def levenshtein(s1, s2):
        if len(s1) < len(s2):
            return levenshtein(s2, s1)
        if not s2:
            return len(s1)
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
            prev = curr
        return prev[-1]

    max_len = max(len(a), len(b))
    if max_len == 0:
        return 100
    dist = levenshtein(a, b)
    return int((1 - dist / max_len) * 100)


def standardize_number_text(val) -> str:
    """Convert number to string representation, handling various inputs."""
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"
    return str(val).strip()
