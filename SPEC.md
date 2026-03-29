# Polymarket AI Trading Bot - Specification

## Project Overview
- **Project Name**: Polymarket AI Trader Bot
- **Type**: Docker-deployable trading bot with web dashboard
- **Core Functionality**: Automated trading on Polymarket prediction markets with AI decision-making
- **Target Users**: Traders who want AI-assisted or automated trading on Polymarket

## Technical Stack
- **Backend**: Python with FastAPI
- **Database**: PostgreSQL (persistent)
- **Frontend**: Modern dashboard with WebSocket for live updates
- **Deployment**: Docker Compose, GitHub-ready

## Features

### 1. Authentication
- Login page with username/password
- Credentials: username `fabian`, password `Cloudflare@2@24ferns`
- Session-based auth

### 2. AI Integration
- Switch between AI providers:
  - **Ollama** (local)
  - **LM Studio** (local)
  - **Gemini** (Google API)
  - **OpenRouter** (aggregator)
- Configurable AI prompts for trading decisions
- Market analysis requests to AI

### 3. Polymarket Trading
- Connect to Polymarket API
- Fetch active markets
- Place buy/sell orders
- Real-time order execution
- Position tracking

### 4. Live Dashboard
- Real-time P&L display
- Active positions list
- Market prices (live updating)
- Trade history
- Bot status (running/stopped)
- Portfolio summary

### 5. Trading Configuration
- Set trading parameters (stake amount, risk level)
- Enable/disable auto-trading
- Select markets to trade
- Configure AI decision-making rules

## Database Schema

### Users
- id, username, password_hash, created_at

### Positions
- id, market_id, market_name, side (yes/no), amount, entry_price, current_price, pnl, created_at

### Trades
- id, market_id, market_name, side, amount, price, tx_hash, status, created_at

### Settings
- id, key, value

### AIConfig
- id, provider, api_key, model, prompt_template, enabled

## API Endpoints

### Auth
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me

### Markets
- GET /api/markets (list active markets)
- GET /api/markets/{id} (market details)

### Trading
- POST /api/trade/buy
- POST /api/trade/sell
- GET /api/positions
- GET /api/trades

### AI
- GET /api/ai/config
- POST /api/ai/config
- POST /api/ai/analyze (get AI opinion on market)
- POST /api/ai/trade (AI decides and executes)

### Dashboard
- GET /api/dashboard/summary (PNL, balance, etc.)
- WebSocket /ws/dashboard (live updates)

## Acceptance Criteria
1. User can login with provided credentials
2. Dashboard shows real-time P&L updates via WebSocket
3. User can configure AI provider and see it working
4. Bot can execute trades on Polymarket (testnet first)
5. All data persists in PostgreSQL
6. Docker Compose deployment works
7. GitHub repository is deployment-ready
