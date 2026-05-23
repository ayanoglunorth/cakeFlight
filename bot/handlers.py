import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.formatting import format_top_flights, render_progress_bar
from bot.search import (
    build_outbound_combinations,
    build_return_combinations,
    search_all_with_progress,
)
from bot.states import FlightSearch
from bot.validators import parse_dates, parse_iata_codes

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.set_state(FlightSearch.departure)
    await message.answer(
        "Uçuş Arama Botuna Hoş Geldiniz!\n\n"
        "Lütfen <b>kalkış havalimanı IATA kodlarını</b> "
        "virgülle ayırarak girin.\n\n"
        "Örnek: <code>IST, SAW, ESB</code>"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("İptal edilecek bir şey yok.")
        return
    await state.clear()
    await message.answer("Arama iptal edildi. Yeniden başlamak için /start yazın.")


@router.message(FlightSearch.departure, F.text)
async def process_departure(message: Message, state: FSMContext) -> None:
    try:
        codes = parse_iata_codes(message.text)
    except ValueError as e:
        await message.answer(f"<b>Hata:</b> {e}\n\nLütfen tekrar deneyin.")
        return
    await state.update_data(departure=codes)
    await state.set_state(FlightSearch.arrival)
    await message.answer(
        f"Kaydedildi: {', '.join(codes)}\n\n"
        "Şimdi <b>varış havalimanı IATA kodlarını</b> "
        "virgülle ayırarak girin.\n\n"
        "Örnek: <code>ALA, TAS, SKD</code>"
    )


@router.message(FlightSearch.arrival, F.text)
async def process_arrival(message: Message, state: FSMContext) -> None:
    try:
        codes = parse_iata_codes(message.text)
    except ValueError as e:
        await message.answer(f"<b>Hata:</b> {e}\n\nLütfen tekrar deneyin.")
        return
    await state.update_data(arrival=codes)
    await state.set_state(FlightSearch.outbound_date)
    await message.answer(
        f"Kaydedildi: {', '.join(codes)}\n\n"
        "Şimdi <b>gidiş tarihlerini</b> "
        "<code>YYYY-MM-DD</code> formatında virgülle ayırarak girin.\n\n"
        "Örnek: <code>2026-08-14, 2026-08-15</code>"
    )


@router.message(FlightSearch.outbound_date, F.text)
async def process_outbound_date(message: Message, state: FSMContext) -> None:
    try:
        dates = parse_dates(message.text)
    except ValueError as e:
        await message.answer(f"<b>Hata:</b> {e}\n\nLütfen tekrar deneyin.")
        return
    await state.update_data(outbound_date=dates)
    await state.set_state(FlightSearch.return_date)
    await message.answer(
        f"Kaydedildi: {', '.join(d.isoformat() for d in dates)}\n\n"
        "Şimdi <b>dönüş tarihlerini</b> "
        "<code>YYYY-MM-DD</code> formatında virgülle ayırarak girin.\n\n"
        "Örnek: <code>2026-08-19, 2026-08-22</code>"
    )


@router.message(FlightSearch.return_date, F.text)
async def process_return_date(message: Message, state: FSMContext) -> None:
    try:
        dates = parse_dates(message.text)
    except ValueError as e:
        await message.answer(f"<b>Hata:</b> {e}\n\nLütfen tekrar deneyin.")
        return
    data = await state.update_data(return_date=dates)
    await state.clear()

    out_combos = build_outbound_combinations(
        data["departure"], data["arrival"], data["outbound_date"]
    )
    ret_combos = build_return_combinations(
        data["arrival"], data["departure"], data["return_date"]
    )

    total = len(out_combos) + len(ret_combos)

    all_combos: list[dict[str, str]] = []
    for origin, dest, d in out_combos:
        all_combos.append({"origin": origin, "destination": dest, "date": d, "leg": "outbound"})
    for origin, dest, d in ret_combos:
        all_combos.append({"origin": origin, "destination": dest, "date": d, "leg": "return"})

    sent = await message.answer(
        f"🔍 Google Flights üzerinden {total} kombinasyon taranıyor..."
    )

    async def update_progress(completed: int, total: int) -> None:
        bar = render_progress_bar(completed, total)
        await sent.edit_text(
            f"🔍 Google Flights üzerinden {total} kombinasyon taranıyor...\n\n{bar}"
        )

    all_results = await search_all_with_progress(all_combos, update_progress)

    outbound_results = [r for r in all_results if r["leg"] == "outbound"]
    return_results = [r for r in all_results if r["leg"] == "return"]

    out_text = format_top_flights(outbound_results, "outbound")
    ret_text = format_top_flights(return_results, "return")
    full = out_text + "\n\n" + ret_text

    await sent.edit_text(full, parse_mode="MarkdownV2")
