# FastAPI WhatsApp-like Message Service

A production-style FastAPI service for ingesting and managing WhatsApp-like messages with HMAC signature validation, idempotent message handling, and comprehensive analytics.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Running the Service

1. **Set up environment variables** (optional, defaults provided):
   ```bash
   export WEBHOOK_SECRET=your-secret-key-here
   export LOG_LEVEL=INFO
   ```

2. **Start the service**:
   ```bash
   make up
   ```

   Or directly with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. **View logs**:
   ```bash
   make logs
   ```

4. **Stop the service**:
   ```bash
   make down
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health & Monitoring

#### `GET /health/live`
Liveness probe endpoint. Always returns 200.

**Response:**
```json
{
  "status": "alive"
}
```

#### `GET /health/ready`
Readiness probe endpoint. Returns 200 only if:
- Database is reachable
- `messages` table exists
- `WEBHOOK_SECRET` is configured

**Response (200):**
```json
{
  "status": "ready"
}
```

**Response (503):**
```json
{
  "status": "not ready",
  "error": "WEBHOOK_SECRET is not configured"
}
```

#### `GET /metrics`
Prometheus-style metrics endpoint. Returns text/plain format with counters and histograms.

**Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{path="/webhook",status="200"} 10.0
http_requests_total{path="/messages",status="200"} 5.0

# HELP webhook_requests_total Total webhook requests
# TYPE webhook_requests_total counter
webhook_requests_total{result="created"} 8.0
webhook_requests_total{result="duplicate"} 2.0

# HELP http_request_latency_ms HTTP request latency in milliseconds
# TYPE http_request_latency_ms histogram
http_request_latency_ms_bucket{le="100"} 10.0
http_request_latency_ms_bucket{le="500"} 15.0
```

### Webhook

#### `POST /webhook`
Ingest inbound messages with HMAC signature validation.

**Headers:**
- `X-Signature`: HMAC-SHA256 signature of request body
- `Content-Type`: `application/json`

**Request Body:**
```json
{
  "message_id": "msg-123",
  "from_msisdn": "+1234567890",
  "to_msisdn": "+0987654321",
  "ts": "2024-01-01T10:00:00Z",
  "text": "Hello, world!"
}
```

**Response (200):**
```json
{
  "status": "ok"
}
```

**Response (401):**
```json
{
  "detail": "invalid signature"
}
```

### Messages

#### `GET /messages`
Retrieve paginated and filtered messages.

**Query Parameters:**
- `limit` (int, 1-100, default: 50): Number of messages to return
- `offset` (int, >=0, default: 0): Number of messages to skip
- `from` (string, optional): Filter by sender MSISDN
- `since` (string, optional): Filter messages since ISO-8601 timestamp
- `q` (string, optional): Case-insensitive substring search on message text

**Response:**
```json
{
  "data": [
    {
      "message_id": "msg-123",
      "from_msisdn": "+1234567890",
      "to_msisdn": "+0987654321",
      "ts": "2024-01-01T10:00:00Z",
      "text": "Hello, world!",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### Statistics

#### `GET /stats`
Get aggregated statistics about messages.

**Response:**
```json
{
  "total_messages": 1000,
  "senders_count": 50,
  "messages_per_sender": [
    {
      "from_msisdn": "+1234567890",
      "count": 150
    },
    {
      "from_msisdn": "+0987654321",
      "count": 120
    }
  ],
  "first_message_ts": "2024-01-01T10:00:00Z",
  "last_message_ts": "2024-01-31T23:59:59Z"
}
```

## cURL Examples

### Send a Message via Webhook

```bash
# Generate HMAC signature
SECRET="your-webhook-secret"
BODY='{"message_id":"msg-001","from_msisdn":"+1234567890","to_msisdn":"+0987654321","ts":"2024-01-01T10:00:00Z","text":"Hello"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### Get Messages with Pagination

```bash
# Get first page
curl "http://localhost:8000/messages?limit=20&offset=0"

# Get messages from specific sender
curl "http://localhost:8000/messages?from=%2B1234567890&limit=10"

# Search messages by text
curl "http://localhost:8000/messages?q=hello&limit=10"

# Get messages since timestamp
curl "http://localhost:8000/messages?since=2024-01-01T00:00:00Z"
```

### Get Statistics

```bash
curl http://localhost:8000/stats
```

### Check Health

```bash
# Liveness probe
curl http://localhost:8000/health/live

# Readiness probe
curl http://localhost:8000/health/ready
```

### Get Metrics

```bash
curl http://localhost:8000/metrics
```

## Design Decisions

### HMAC Verification

**Implementation:**
- Uses HMAC-SHA256 for signature validation
- Signature computed from raw request body bytes
- Secret stored in `WEBHOOK_SECRET` environment variable
- Uses `hmac.compare_digest()` for constant-time comparison to prevent timing attacks

**Rationale:**
- Ensures message authenticity and integrity
- Prevents replay attacks when combined with idempotency
- Standard approach for webhook security
- Constant-time comparison prevents timing-based signature attacks

**Flow:**
1. Read raw request body bytes
2. Extract `X-Signature` header
3. Compute expected signature: `HMAC-SHA256(secret, body)`
4. Compare signatures using constant-time comparison
5. Return 401 if invalid, proceed if valid

### Idempotency

**Implementation:**
- Uses `message_id` as PRIMARY KEY in database
- Duplicate inserts return `"duplicate"` status without raising exceptions
- Webhook endpoint always returns 200 on valid signature, regardless of duplicate status

**Rationale:**
- Prevents duplicate message processing
- Handles webhook retries gracefully
- Ensures exactly-once message ingestion
- Database constraint provides atomic idempotency check

**Flow:**
1. Validate signature and payload
2. Attempt to insert message with `message_id` as PRIMARY KEY
3. If `IntegrityError` (duplicate): return `"duplicate"` status
4. If successful: return `"created"` status
5. Always return 200 HTTP status on valid signature

### Pagination

**Implementation:**
- Uses `LIMIT` and `OFFSET` for pagination
- Total count calculated separately (ignores limit/offset)
- Default limit: 50, max limit: 100
- Ordering: `ts ASC, message_id ASC` for deterministic results

**Rationale:**
- Efficient for large datasets
- Total count provides accurate pagination metadata
- Deterministic ordering ensures consistent results across pages
- Secondary sort on `message_id` handles messages with identical timestamps

**Features:**
- `total` field reflects full filtered result set
- `limit` and `offset` returned in response for client convenience
- Deterministic ordering prevents duplicate or missed messages

### Stats Logic

**Implementation:**
- Aggregates statistics using SQL queries
- `messages_per_sender` limited to top 10, sorted descending
- Timestamps return `null` when no messages exist
- Single query for first/last timestamps

**Rationale:**
- Efficient single-pass aggregation
- Top 10 provides most relevant insights without overwhelming response
- Null timestamps clearly indicate empty state
- Separate queries optimize for different aggregation needs

**Statistics Computed:**
- `total_messages`: Total count of all messages
- `senders_count`: Count of unique senders
- `messages_per_sender`: Top 10 senders by message count (descending)
- `first_message_ts`: Earliest message timestamp
- `last_message_ts`: Latest message timestamp

## Architecture

### Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, middleware, lifespan
│   ├── config.py            # Environment configuration (12-factor)
│   ├── models.py            # Database schema initialization
│   ├── storage.py           # Database operations
│   ├── logging_utils.py     # Structured JSON logging
│   ├── metrics.py           # Prometheus-style metrics
│   └── routers/
│       ├── __init__.py      # Router exports
│       ├── webhook.py       # POST /webhook
│       ├── messages.py     # GET /messages
│       ├── stats.py         # GET /stats
│       ├── health.py        # GET /health/*
│       └── metrics.py       # GET /metrics
├── tests/                   # Unit tests
├── data/                    # SQLite database storage
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml      # Docker Compose configuration
├── Makefile                 # Convenience commands
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

### Technology Stack

- **Framework**: FastAPI 0.104.1
- **Database**: SQLite (via sqlite3)
- **Server**: Uvicorn with standard extras
- **Validation**: Pydantic 2.5.0
- **Configuration**: Pydantic Settings 2.1.0
- **Logging**: Structured JSON logs
- **Metrics**: Custom Prometheus-style metrics collector

### Features

- ✅ Exactly-once message ingestion (idempotent)
- ✅ HMAC-SHA256 signature validation
- ✅ Structured JSON logging with request IDs
- ✅ Prometheus-style metrics
- ✅ Health probes (liveness/readiness)
- ✅ Paginated and filterable message queries
- ✅ Aggregated statistics
- ✅ 12-factor app configuration
- ✅ Docker Compose deployment
- ✅ Multi-stage Dockerfile for small images

## Configuration

### Environment Variables

- `DATABASE_URL`: SQLite database path (default: `sqlite:///./data/messages.db`)
- `WEBHOOK_SECRET`: Secret key for HMAC signature validation (required)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Database

- SQLite database stored in `/data/app.db` (Docker) or `./data/messages.db` (local)
- Schema initialized automatically on startup
- Idempotency enforced via PRIMARY KEY on `message_id`

## Testing

Run tests with:
```bash
make test
```

Or directly:
```bash
pytest tests/ -v
```
## Design Decisions

- **Idempotency**: Enforced via SQLite PRIMARY KEY on message_id; duplicates handled gracefully.
- **HMAC verification**: Computed on raw request body bytes using HMAC-SHA256 and constant-time comparison.
- **Validation**: Pydantic models with field aliases to map external API fields (`from`, `to`) to internal schema.
- **Pagination**: Deterministic ordering by ts ASC, message_id ASC with total count independent of limit/offset.
- **Observability**: Structured JSON logs per request and Prometheus-style metrics.

## Setup Used (AI Tools Disclosure)

This project was developed with the assistance of AI coding tools: Cursor AI & ChatGPT.

The implementation follows FastAPI best practices, production-ready patterns, and industry standards for webhook handling, idempotency, and observability.

Create a `.env` file for local development.

