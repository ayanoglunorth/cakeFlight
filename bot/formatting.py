import re

MARKDOWN_V2_CHARS = re.compile(r"([_*\[\]()~`>#+\-=\|{}.!])")


PROGRESS_BAR_LENGTH = 20


def render_progress_bar(completed: int, total: int) -> str:
    if total <= 0:
        return ""
    filled = int(PROGRESS_BAR_LENGTH * completed / total)
    bar = "█" * filled + "░" * (PROGRESS_BAR_LENGTH - filled)
    return f"{bar} {completed}/{total}"


def escape_markdown_v2(text: str) -> str:
    return MARKDOWN_V2_CHARS.sub(r"\\\1", text)


def _format_price_display(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.replace("TRY", "₺").strip()
    return cleaned


def format_top_flights(results: list[dict], leg: str) -> str:
    header = "🛫 EN UCUZ 5 GİDİŞ:" if leg == "outbound" else "🛬 EN UCUZ 5 DÖNÜŞ:"
    lines: list[str] = [header, ""]

    ok_results = [r for r in results if r["status"] == "ok" and r.get("lowest_price") is not None]
    ok_results.sort(key=lambda r: r["lowest_price"])

    if not ok_results:
        lines.append("Uçuş bulunamadı")
        return "\n".join(lines)

    for i, r in enumerate(ok_results[:5], start=1):
        route = f"{r['origin']}→{r['destination']}"
        raw_display = r.get("cheapest_price_display") or ""
        price = _format_price_display(raw_display) or f"₺{r['lowest_price']:.0f}"
        airline = r.get("cheapest_airline") or "Bilinmiyor"

        entry_prefix = escape_markdown_v2(f"{i}. {r['date']} - {route}: ")
        entry_suffix = escape_markdown_v2(f" & {airline}")
        price_escaped = escape_markdown_v2(price)

        flight_url = r.get("flight_url")
        if flight_url:
            entry = f"{entry_prefix}[{price_escaped}]({flight_url}){entry_suffix}"
        else:
            entry = f"{entry_prefix}{price_escaped}{entry_suffix}"
        lines.append(entry)

    return "\n".join(lines)
