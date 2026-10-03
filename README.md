# cakeFlight

cakeFlight is a Telegram bot for comparing flight options across departure airports, arrival airports, and travel dates. It guides the user through the search inputs in chat and returns formatted results from Google Flights lookups.

## Features

- Multi-airport IATA input for departure and arrival locations
- Multiple outbound and return date combinations
- Guided Telegram conversation flow with input validation
- Search progress messages and formatted flight results
- `/start` and `/cancel` commands

## Requirements

- Python 3.10 or later
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Installation

```bash
git clone https://github.com/ayanoglunorth/cakeFlight.git
cd cakeFlight
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set the bot token in your environment before starting the app:

```bash
export BOT_TOKEN=your_telegram_bot_token
python -m bot
```

On Windows PowerShell, use `$env:BOT_TOKEN = "your_telegram_bot_token"`.

## Usage

1. Send `/start` to the bot.
2. Enter comma-separated departure and arrival airport IATA codes.
3. Provide outbound and return dates in `YYYY-MM-DD` format.
4. Review the returned flight options.

## Project structure

```text
bot/
  __main__.py      Application entry point
  handlers.py      Telegram conversation handlers
  search.py        Flight-search orchestration
  validators.py    Input parsing and validation
  formatting.py    Result formatting
```

## Security

Keep `BOT_TOKEN` out of source control. Use environment variables or a local, ignored configuration file for credentials.

## Disclaimer

cakeFlight is an independent project and is not affiliated with Google or Google Flights. Use it according to the terms of the services you access.
