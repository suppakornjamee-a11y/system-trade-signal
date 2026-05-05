# Railway Backend Deploy

This backend is ready to run as a Railway web service. The in-app scheduler can scan trade signals and send Telegram notifications without running the project locally.

## Railway service settings

Use these settings when creating the backend service from the GitHub repo:

- Root Directory: `/backend`
- Config File: `/backend/railway.toml`
- Public Networking: Generate a Railway domain
- Healthcheck Path: `/health`

Railway will detect `backend/Dockerfile` and run the FastAPI app on the `$PORT` variable it provides.

## Required variables

Set these in the Railway service Variables tab:

```env
DEBUG=false
CACHE_TTL_SECONDS=30
SCREENER_CACHE_TTL_SECONDS=300
SCREENER_INCLUDE_NEWS=false
NEWS_API_KEY=
ANTHROPIC_API_KEY=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SIGNAL_NOTIFICATIONS_ENABLED=true
SIGNAL_POLL_INTERVAL_SECONDS=300
SIGNAL_COOLDOWN_MINUTES=30
SIGNAL_MIN_SCORE=70
SIGNAL_MIN_RISK_REWARD=1.2
SIGNAL_MARKETS=us,th,cn
```

## Telegram setup

1. Create a bot with `@BotFather`.
2. Copy the token into `TELEGRAM_BOT_TOKEN`.
3. Send any message to the bot from the Telegram account or group that should receive alerts.
4. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`.
5. Copy `message.chat.id` into `TELEGRAM_CHAT_ID`.

## Useful endpoints

- `GET /health`
- `GET /api/signals?market=us`
- `POST /api/signals/scan`
- `GET /api/screener/today?market=us`

The background scanner starts only when `SIGNAL_NOTIFICATIONS_ENABLED=true`.
