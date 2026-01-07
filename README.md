# FastAPI WhatsApp-like Message Service

A production-style FastAPI service for ingesting and managing WhatsApp-like messages with:
- Exactly-once message ingestion
- HMAC signature validation
- Paginated/filterable message queries
- Prometheus-style metrics
- Structured JSON logging
- Docker Compose deployment with SQLite

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc

## Project Structure

```
.
├── app/
│   ├── __init__.py         # Package initialization
│   ├── main.py             # FastAPI app, middleware, routes
│   ├── models.py           # SQLite database models and initialization
│   ├── storage.py          # Database operations
│   ├── logging_utils.py    # JSON logger setup
│   ├── metrics.py          # Prometheus-style metrics helpers
│   └── config.py           # Environment configuration (12-factor)
├── tests/
│   ├── __init__.py
│   ├── test_webhook.py     # Webhook tests (valid insert, duplicate, signature)
│   ├── test_messages.py    # Messages endpoint tests (pagination + filters)
│   └── test_stats.py       # Stats endpoint tests
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── Makefile                # Common commands
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── .gitignore              # Git ignore file
```

## Endpoints

- `POST /webhook` - Ingest WhatsApp-like messages (with HMAC validation)
- `GET /messages` - Paginated and filterable messages endpoint
- `GET /stats` - Analytical statistics endpoint
- `GET /metrics` - Prometheus-style metrics endpoint
- `GET /health` - Health check endpoint
- `GET /ready` - Readiness probe endpoint

## Running with Docker Compose

```bash
# Build and start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## Development

```bash
# Install dependencies
make install

# Run development server
make run

# Run tests
make test
```

## Environment Variables

The application uses 12-factor app principles. Configure via environment variables:

- `DATABASE_PATH` - Path to SQLite database (default: `messages.db`)
- `WEBHOOK_SECRET` - Secret key for HMAC signature validation
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `ENVIRONMENT` - Environment name (default: `development`)

Create a `.env` file for local development.

