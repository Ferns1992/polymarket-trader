# Polymarket AI Trading Bot

AI-powered trading bot for Polymarket prediction markets with live dashboard.

## Features

- **AI Trading**: Multiple AI provider support (Ollama, LM Studio, Gemini, OpenRouter)
- **Live Dashboard**: Real-time P&L tracking with WebSocket updates
- **Automated Trading**: Let AI analyze and execute trades automatically
- **Docker Deployable**: Easy deployment to VPS with Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### Deployment

1. Clone the repository
2. Run Docker Compose:

```bash
docker-compose up -d
```

3. Access the dashboard at `http://localhost`

### Default Login

- Username: `fabian`
- Password: `Cloudflare@2@24ferns`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `SECRET_KEY` | Application secret key | Auto-generated |
| `POLYMARKET_API_URL` | Polymarket API endpoint | `https://clob.polymarket.com` |

## AI Providers

### Ollama (Local)
- Download from https://ollama.ai
- Default URL: `http://localhost:11434`

### LM Studio (Local)
- Download from https://lmstudio.ai
- Default URL: `http://localhost:1234/v1`

### OpenRouter (Cloud)
- Get API key from https://openrouter.ai

### Gemini (Google)
- Get API key from https://aistudio.google.com/app/apikey

## API Endpoints

- `POST /api/auth/login` - Login
- `GET /api/markets` - List markets
- `POST /api/trade/buy` - Execute buy order
- `POST /api/ai/analyze` - Get AI market analysis
- `GET /api/dashboard/summary` - Get P&L summary
- `WS /api/ws/dashboard` - Live dashboard updates

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run database init
python -m app.init_db

# Run development server
uvicorn app.main:app --reload
```

## License

MIT
