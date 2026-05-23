from aiogram.fsm.state import State, StatesGroup


class FlightSearch(StatesGroup):
    departure = State()
    arrival = State()
    outbound_date = State()
    return_date = State()
