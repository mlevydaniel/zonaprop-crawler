# Zonaprop Crawler

Zonaprop Crawler is a small Python project that automates the scraping of
real-estate listings from [Zonaprop](https://www.zonaprop.com.ar/) and
exports them as structured JSON. It is designed as a simple, scriptable
tool you can extend or integrate into your own analysis pipelines.


### Features

- **Paginated scraping**: follows Zonaprop result pages starting from a
  configurable URL.
- **Structured data model**: listings are represented by a `Listing`
  dataclass and serialized to JSON.
- **Detail-page enrichment**: for each listing card, the crawler fetches
  the detail page to extract additional features (areas, rooms, publisher).
- **Basic rate limiting & retries** via `ScraperService`.
- **Telegram helpers**: simple utilities to send Telegram messages and
  to retrieve your chat/user IDs using a bot.


## Requirements

- Python 3.9+ (recommended)
- The following Python packages:
  - `requests`
  - `beautifulsoup4`
  - `python-telegram-bot` (for the Telegram scripts)

You can install these with:

```bash
pip install requests beautifulsoup4 python-telegram-bot
```


## Project structure

```text
main.py                     # CLI entry point for the scraper
src/
  models.py                 # Listing dataclass and helpers
  repositories.py           # ListingRepository + ZonapropRepository
  scraper_manager.py        # Orchestrates repository across pages
  services.py               # ScraperService (HTTP client, rate limiting)
  utils.py                  # Text/HTML parsing utilities
send_telegram_message.py    # Helper to send a message via Telegram Bot API
start_telegram_bot.py       # Minimal bot to discover chat/user IDs
README.md                   # This file
```


## Configuration

The core scraper does not require credentials, but you **must** provide:

- A starting Zonaprop URL (default is configured in `main.py`).
- The maximum number of pages to traverse.

For the Telegram helper scripts you will need:

- A **Telegram bot token** (obtained via `@BotFather`).
- A **chat id** (which can be discovered with `start_telegram_bot.py`).

It is strongly recommended to keep tokens and chat IDs outside of the
source code (e.g. in environment variables or a `.env` file).


## Usage

### 1. Run the scraper from the command line

From the project root:

```bash
python main.py \
  --max_pages 2 \
  --output zonaprop_listings.json \
  --url "https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-caballito.html"
```

**Arguments**

- `--max_pages` (int, default: `2`):  
  Maximum number of result pages to scrape. The scraper stops early if
  there are fewer pages.

- `--output` (str, default: `zonaprop_caballito_rentals.json`):  
  Path to the JSON file where results are saved.

- `--url` (str, default: a Caballito rentals URL):  
  Starting Zonaprop search URL. You can change this to any compatible
  Zonaprop listing search page.

The output JSON file will contain a list of listing objects as exported
by `Listing.to_dict()`, with dates in ISO 8601 format.


### 2. Discover your Telegram chat ID

1. Create a bot with `@BotFather` and obtain a token.
2. Edit `start_telegram_bot.py` and set:

   ```python
   BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
   ```

3. Run:

   ```bash
   python start_telegram_bot.py
   ```

4. Send any message to your bot from Telegram.  
   The bot will reply with your **chat id** and **user id**, which you
   can reuse in other scripts.


### 3. Send a test Telegram message

Use `send_telegram_message.py` either by importing it or running it
directly.

**As a script**

Edit the placeholders:

```python
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
MESSAGE = "Hello, this is a test message from Python!"
```

Then run:

```bash
python send_telegram_message.py
```

**As a library**

```python
from send_telegram_message import send_telegram_message

response = send_telegram_message(
    bot_token="YOUR_TELEGRAM_BOT_TOKEN",
    chat_id="YOUR_CHAT_ID",
    message="Hello from Zonaprop crawler!",
)
print(response)
```


## Limitations and notes

- The scraper relies on Zonaprop's HTML structure and data-qa attributes.
  If the site layout changes, the selectors in `ZonapropRepository`
  may need to be updated.
- A random delay is applied before each HTTP request; this is a simple
  mechanism to be "polite" with the target site, but it does not replace
  reading and respecting the site's terms of use and robots.txt.
- This project is intended for educational and personal use. Make sure
  you comply with Zonaprop's terms of service and local regulations
  before running it at scale.


## Development

If you want to extend the project:

- Add new fields to the `Listing` dataclass if you need more information
  from the detail pages.
- Add new repository implementations (e.g. for other portals) by
  subclassing `ListingRepository`.
- Add unit tests around `utils.py` and the parsing logic inside
  `ZonapropRepository` using saved HTML fixtures.

Contributions, experiments and refactors are welcome—this is a small,
intentionally simple codebase meant to be hacked on.
