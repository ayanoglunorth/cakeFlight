import asyncio
import logging
import re
from collections.abc import Sequence
from datetime import date
from itertools import product
from typing import Any

from fast_flights import FlightData, Passengers
from fast_flights.flights_impl import TFSData
from fast_flights import flights_pb2 as PB
from primp import Client
from selectolax.lexbor import LexborHTMLParser, LexborNode

logger = logging.getLogger(__name__)

MAX_CONCURRENT_TASKS = 1
REQUEST_DELAY = 3

Combination = tuple[str, str, str]


def build_outbound_combinations(
    departures: Sequence[str],
    arrivals: Sequence[str],
    outbound_dates: Sequence[date],
) -> list[Combination]:
    return [
        (dep, arr, d.isoformat())
        for dep, arr, d in product(departures, arrivals, outbound_dates)
    ]


def build_return_combinations(
    arrivals: Sequence[str],
    departures: Sequence[str],
    return_dates: Sequence[date],
) -> list[Combination]:
    return [
        (arr, dep, d.isoformat())
        for arr, dep, d in product(arrivals, departures, return_dates)
    ]


def _parse_price(price_str: str) -> float | None:
    try:
        cleaned = re.sub(r"[^\d.,-]", "", price_str)
        cleaned = cleaned.replace(",", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _build_url(origin: str, destination: str, date_str: str) -> str:
    fd = FlightData(date=date_str, from_airport=origin, to_airport=destination)
    passengers = Passengers(adults=1)
    tfs = TFSData(
        flight_data=[fd],
        seat=PB.Seat.ECONOMY,
        trip=PB.Trip.ONE_WAY,
        passengers=passengers,
    )
    data_b64 = tfs.as_b64().decode()
    return f"https://www.google.com/travel/flights?tfs={data_b64}&hl=en&tfu=EgQIABABIgA&curr="


def _parse_flights(html: str) -> list[dict[str, Any]]:
    parser = LexborHTMLParser(html)
    flights: list[dict[str, Any]] = []

    containers = parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')
    for i, container in enumerate(containers):
        items = container.css("ul.Rk10dc li")
        if not items:
            continue

        # Skip last item for non-first containers (duplicate "show more" row)
        item_range = items if i == 0 else items[:-1]

        for item in item_range:
            _parse_single_flight(item, flights)

    return flights


def _parse_single_flight(
    item: LexborNode, flights: list[dict[str, Any]]
) -> None:
    price_el = item.css_first(".YMlIz.FpEdX")
    if price_el is None:
        return
    price_text = price_el.text() or "0"

    name = ""
    dp_ar_node = item.css("span.mv1WYe div")
    departure_time = ""
    arrival_time = ""
    duration = ""
    stops_text = ""

    # Find all div.sSHqwe.tPgKwe.ogfYpf elements, get the first one's span text as airline
    for node in item.css("div.sSHqwe.tPgKwe.ogfYpf"):
        span = node.css_first("span")
        if span is not None:
            txt = span.text(strip=True)
            if txt and not name:
                name = txt

    # Duration
    for node in item.css("li div.Ak5kof div"):
        txt = node.text()
        if txt and ("hr" in txt or "min" in txt):
            duration = txt
            break

    # Stops
    for node in item.css(".BbR8Ec .ogfYpf"):
        txt = node.text()
        if txt and txt.strip():
            stops_text = txt.strip()
            break

    # Departure / arrival
    if len(dp_ar_node) >= 2:
        departure_time = dp_ar_node[0].text(strip=True)
        arrival_time = dp_ar_node[1].text(strip=True)

    try:
        stops_fmt = 0 if stops_text == "Nonstop" else int(stops_text.split(" ", 1)[0])
    except (ValueError, IndexError):
        stops_fmt = "Unknown"

    price_clean = price_text.replace(",", "")
    flights.append(
        {
            "name": name,
            "price": price_clean,
            "price_display": price_text,
            "departure": " ".join(departure_time.split()),
            "arrival": " ".join(arrival_time.split()),
            "duration": duration,
            "stops": stops_fmt,
        }
    )


async def search_single(
    origin: str,
    destination: str,
    date_str: str,
    leg: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        logger.info(
            "Searching %s: %s → %s on %s", leg, origin, destination, date_str
        )
        try:
            url = _build_url(origin, destination, date_str)

            def _fetch() -> str:
                client = Client(impersonate="chrome_126", verify=False)
                res = client.get(url)
                assert res.status_code == 200
                return res.text

            html = await asyncio.to_thread(_fetch)
            parsed_flights = _parse_flights(html)

            flights = []
            lowest_price: float | None = None
            cheapest_airline: str | None = None
            cheapest_price_display: str | None = None

            for f in parsed_flights:
                price = _parse_price(f["price"])
                flights.append(
                    {
                        "airline": f["name"],
                        "price_display": f.get("price_display", f["price"]),
                        "departure": f["departure"],
                        "arrival": f["arrival"],
                        "duration": f["duration"],
                        "stops": f["stops"],
                        "price": price,
                    }
                )
                if lowest_price is None or (price is not None and price < lowest_price):
                    lowest_price = price
                    cheapest_airline = f["name"]
                    cheapest_price_display = f.get("price_display", f["price"])

            await asyncio.sleep(REQUEST_DELAY)

            return {
                "origin": origin,
                "destination": destination,
                "date": date_str,
                "leg": leg,
                "status": "ok",
                "lowest_price": lowest_price,
                "cheapest_airline": cheapest_airline,
                "cheapest_price_display": cheapest_price_display,
                "flight_count": len(flights),
                "flights": flights,
                "flight_url": url,
            }

        except Exception as e:
            logger.error(
                "Search failed for %s→%s on %s: %s",
                origin,
                destination,
                date_str,
                e,
            )
            await asyncio.sleep(REQUEST_DELAY)
            return {
                "origin": origin,
                "destination": destination,
                "date": date_str,
                "leg": leg,
                "status": "error",
                "error": str(e),
            }


async def search_all_with_progress(
    combinations: list[dict[str, str]],
    on_progress: object,
) -> list[dict]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    total = len(combinations)
    completed = 0
    results: list[dict] = [None] * total

    async def worker(idx: int, combo: dict[str, str]) -> None:
        nonlocal completed
        result = await search_single(
            combo["origin"],
            combo["destination"],
            combo["date"],
            combo["leg"],
            semaphore,
        )
        results[idx] = result
        completed += 1
        if on_progress:
            await on_progress(completed, total)

    tasks = [worker(i, c) for i, c in enumerate(combinations)]
    await asyncio.gather(*tasks)
    return results


async def search_leg(
    combinations: Sequence[Combination],
    leg: str,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    tasks = [
        search_single(origin, dest, date_str, leg, semaphore)
        for origin, dest, date_str in combinations
    ]
    return await asyncio.gather(*tasks)
