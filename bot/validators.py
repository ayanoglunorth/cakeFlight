import re
from datetime import date, datetime


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IATA_PATTERN = re.compile(r"^[A-Z]{3}$")


def parse_iata_codes(raw: str) -> list[str]:
    codes = [code.strip().upper() for code in raw.split(",") if code.strip()]
    if not codes:
        raise ValueError("Lütfen en az bir havalimanı kodu girin.")
    for code in codes:
        if not IATA_PATTERN.match(code):
            raise ValueError(
                f"Geçersiz IATA kodu: {code}. Her kod tam olarak 3 harften oluşmalıdır (ör. IST, SAW)."
            )
    return codes


def parse_dates(raw: str) -> list[date]:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if not items:
        raise ValueError("Lütfen en az bir tarih girin.")
    result: list[date] = []
    for item in items:
        if not DATE_PATTERN.match(item):
            raise ValueError(
                f"Geçersiz tarih formatı: {item}. YYYY-MM-DD şeklinde girin (ör. 2026-08-14)."
            )
        try:
            dt = datetime.strptime(item, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Geçersiz tarih: {item}. YYYY-MM-DD şeklinde girin (ör. 2026-08-14).")
        if dt < date.today():
            raise ValueError(f"{item} tarihi geçmişte. Lütfen ileri bir tarih girin.")
        result.append(dt)
    return result
