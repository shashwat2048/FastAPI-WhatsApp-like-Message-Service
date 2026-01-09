# FastAPI Backend - Architecture & Flow Documentation

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Request Flow](#request-flow)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow](#data-flow)
6. [Key Features](#key-features)

---

## 🎯 Overview

This is a **production-ready FastAPI service** that:
- Receives WhatsApp-like messages via webhook (with HMAC signature validation)
- Stores messages in SQLite database (idempotent - exactly once delivery)
- Provides paginated/filterable message retrieval
- Exposes analytics endpoints
- Emits structured JSON logs and Prometheus metrics
- Runs in Docker with 12-factor app configuration

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (curl/browser)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         RequestLoggingMiddleware                      │  │
│  │  • Generate request_id (UUID)                         │  │
│  │  • Measure latency                                    │  │
│  │  • Log structured JSON                                │  │
│  │  • Record metrics                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│                        ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              CORS Middleware                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                        │                                    │
│                        ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Routers                           │  │
│  │  • /webhook    - POST (ingest messages)              │  │
│  │  • /messages   - GET  (list messages)                │  │
│  │  • /stats      - GET  (analytics)                     │  │
│  │  • /health/*   - GET  (liveness/readiness)            │  │
│  │  • /metrics    - GET  (Prometheus metrics)            │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Storage    │ │   Logging    │ │   Metrics    │
│   (SQLite)   │ │   (JSON)     │ │ (Prometheus) │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🔄 Request Flow

### 1. Application Startup Flow

```
1. FastAPI app created (main.py)
   ↓
2. Lifespan handler executes (startup)
   ↓
3. init_schema() called
   ↓
4. Database connection created
   ↓
5. CREATE TABLE IF NOT EXISTS messages
   ↓
6. Application ready to accept requests
```

### 2. Incoming Request Flow (e.g., POST /webhook)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Request arrives at FastAPI                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: RequestLoggingMiddleware intercepts                │
│  • Generate UUID request_id                                  │
│  • Store in request.state.request_id                         │
│  • Record start_time                                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: CORS Middleware (if needed)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Router handles request                              │
│  For /webhook:                                               │
│    a) Read raw body bytes                                    │
│    b) Extract X-Signature header                             │
│    c) Verify HMAC signature                                  │
│    d) Parse & validate JSON payload                          │
│    e) Insert message into database                           │
│    f) Return response                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Middleware logs response                             │
│  • Calculate latency_ms = (end_time - start_time) * 1000     │
│  • Log structured JSON with:                                 │
│    - request_id, method, path, status, latency_ms           │
│  • Record metrics:                                           │
│    - http_requests_total{path, status}                      │
│    - http_request_latency_ms                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Response sent to client                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 Component Breakdown

### 1. **main.py** - Application Entry Point
**Purpose**: Initialize FastAPI app, configure middleware, register routers

**Key Components**:
- `lifespan()`: Startup/shutdown handler (replaces deprecated `@app.on_event`)
- `RequestLoggingMiddleware`: Logs every request as structured JSON
- Router registration: Includes all endpoint routers

**Flow**:
```python
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(webhook_router, prefix="/webhook")
# ... other routers
```

---

### 2. **config.py** - Configuration Management
**Purpose**: 12-factor app configuration using environment variables

**Key Features**:
- Uses `pydantic_settings.BaseSettings`
- Loads from `.env` file or environment
- No hardcoded secrets

**Configuration Variables**:
- `DATABASE_URL`: SQLite database path
- `WEBHOOK_SECRET`: HMAC secret for signature validation
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

---

### 3. **models.py** - Database Schema
**Purpose**: Initialize SQLite database and create schema

**Key Functions**:
- `parse_database_url()`: Converts `sqlite:////data/app.db` → `/data/app.db`
- `init_db()`: Creates database connection and `messages` table
- `init_schema()`: Called on startup (gracefully handles errors)

**Database Schema**:
```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY NOT NULL,  -- Ensures idempotency
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,                       -- ISO-8601 timestamp
    text TEXT,                              -- Optional message text
    created_at TEXT NOT NULL                -- When record was created
)
```

---

### 4. **storage.py** - Database Operations
**Purpose**: CRUD operations for messages

**Key Functions**:

#### `insert_message(data) → "created" | "duplicate"`
- **Idempotency**: Uses `message_id` PRIMARY KEY
- **Behavior**: 
  - First insert → returns `"created"`
  - Duplicate `message_id` → catches `IntegrityError` → returns `"duplicate"`
- **No exceptions**: Duplicates are handled gracefully

#### `list_messages(filters, limit, offset) → (rows, total)`
- **Filters**:
  - `from_msisdn`: Exact match on sender
  - `since`: `ts >= since` (timestamp comparison)
  - `q`: Case-insensitive substring search in `text`
- **Ordering**: `ts ASC, message_id ASC` (deterministic)
- **Pagination**: `LIMIT` and `OFFSET`
- **Total**: Counts all matching rows (ignores pagination)

#### `compute_stats() → Dict`
- **Metrics**:
  - `total_messages`: COUNT(*)
  - `senders_count`: COUNT(DISTINCT from_msisdn)
  - `messages_per_sender`: Top 10 senders (GROUP BY, ORDER BY count DESC)
  - `first_message_ts`: MIN(ts)
  - `last_message_ts`: MAX(ts)

---

### 5. **routers/webhook.py** - Message Ingestion
**Purpose**: Receive and validate webhook messages

**Flow**:
```
1. Read raw body bytes (for HMAC verification)
2. Extract X-Signature header
3. Verify HMAC-SHA256 signature
   ├─ Invalid → 401 "invalid signature"
   └─ Valid → Continue
4. Parse JSON payload
5. Validate with Pydantic WebhookPayload:
   ├─ message_id: non-empty string
   ├─ from/to: E.164 format (+1234567890)
   ├─ ts: ISO-8601 UTC with Z suffix
   └─ text: optional, max 4096 chars
6. Insert message (idempotent)
7. Log webhook event
8. Record metrics
9. Return 200 {"status": "ok"}
```

**HMAC Signature Verification**:
```python
expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
is_valid = hmac.compare_digest(expected, signature)  # Constant-time comparison
```

**Idempotency**:
- Same `message_id` sent twice → First = "created", Second = "duplicate"
- Both return 200 OK (no error)
- Database prevents duplicate inserts via PRIMARY KEY

---

### 6. **routers/messages.py** - Message Retrieval
**Purpose**: Paginated and filtered message listing

**Query Parameters**:
- `limit`: 1-100 (default: 50)
- `offset`: >=0 (default: 0)
- `from`: Filter by sender MSISDN (aliased from `from_msisdn`)
- `since`: Filter messages where `ts >= since`
- `q`: Case-insensitive text search

**Response Format**:
```json
{
  "data": [...],      // Array of message objects
  "total": 150,       // Total matching messages (ignores pagination)
  "limit": 50,
  "offset": 0
}
```

**Example**:
```
GET /messages?from=%2B919876543210&limit=10&offset=0
→ Returns first 10 messages from +919876543210
→ total = all messages from that sender
```

---

### 7. **routers/stats.py** - Analytics
**Purpose**: Aggregated message statistics

**Response**:
```json
{
  "total_messages": 1000,
  "senders_count": 25,
  "messages_per_sender": [
    {"from_msisdn": "+919876543210", "count": 150},
    {"from_msisdn": "+1234567890", "count": 120},
    ...
  ],
  "first_message_ts": "2026-01-01T00:00:00Z",
  "last_message_ts": "2026-01-07T12:00:00Z"
}
```

---

### 8. **routers/health.py** - Health Checks
**Purpose**: Kubernetes/Docker health probes

**Endpoints**:
- `GET /health/live`: Always returns 200 (liveness probe)
- `GET /health/ready`: Returns 200 only if:
  - `WEBHOOK_SECRET` is configured
  - Database is reachable
  - `messages` table exists
  - Otherwise returns 503

---

### 9. **routers/metrics.py** - Prometheus Metrics
**Purpose**: Expose Prometheus-style metrics

**Metrics Exposed**:
```
http_requests_total{path="/webhook",status="200"} 150
http_requests_total{path="/messages",status="200"} 45
webhook_requests_total{result="created"} 100
webhook_requests_total{result="duplicate"} 5
http_request_latency_ms_count 195
http_request_latency_ms_sum 1234.56
```

---

### 10. **logging_utils.py** - Structured Logging
**Purpose**: JSON-formatted logs (one object per line)

**Log Format**:
```json
{
  "ts": "2026-01-07T12:00:00.123456Z",
  "level": "INFO",
  "request_id": "uuid-here",
  "method": "POST",
  "path": "/webhook",
  "status": 200,
  "latency_ms": 5.23,
  "message_id": "msg-123",
  "dup": false,
  "result": "created"
}
```

**Features**:
- `JSONFormatter`: Converts log records to JSON
- `RequestLoggingMiddleware`: Logs every HTTP request
- `log_webhook_event()`: Helper for webhook-specific logging

---

### 11. **metrics.py** - Metrics Collection
**Purpose**: In-memory Prometheus-style metrics

**MetricsCollector Class**:
- **Counters**: `http_requests_total`, `webhook_requests_total`
- **Histograms**: `http_request_latency_ms`
- **Labels**: Support for key-value pairs (e.g., `{path="/webhook", status="200"}`)

**Functions**:
- `record_http_request(path, status)`: Increment HTTP counter
- `record_webhook_request(result)`: Increment webhook counter
- `record_latency(latency_ms)`: Record latency observation
- `get_metrics()`: Generate Prometheus text format

---

## 📊 Data Flow

### Webhook Message Ingestion Flow

```
┌──────────────┐
│   Client     │
│  (WhatsApp)  │
└──────┬───────┘
       │ POST /webhook
       │ Body: {"message_id": "...", "from": "...", ...}
       │ Header: X-Signature: <HMAC>
       ▼
┌─────────────────────────────────────┐
│  FastAPI /webhook endpoint          │
│  1. Read body_bytes                  │
│  2. Verify HMAC signature            │
│  3. Parse & validate JSON             │
│  4. Call insert_message()            │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  storage.insert_message()            │
│  • INSERT INTO messages ...         │
│  • If IntegrityError → "duplicate"  │
│  • Else → "created"                 │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  SQLite Database                     │
│  • PRIMARY KEY on message_id         │
│  • Prevents duplicates               │
└─────────────────────────────────────┘
```

### Message Retrieval Flow

```
┌──────────────┐
│   Client     │
│  (Browser)   │
└──────┬───────┘
       │ GET /messages?from=+123&limit=10
       ▼
┌─────────────────────────────────────┐
│  FastAPI /messages endpoint          │
│  1. Parse query parameters            │
│  2. Build filters dict                │
│  3. Call list_messages()             │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  storage.list_messages()             │
│  1. Build WHERE clause               │
│  2. COUNT(*) for total               │
│  3. SELECT with LIMIT/OFFSET         │
│  4. ORDER BY ts ASC, message_id ASC │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  SQLite Database                     │
│  • Query messages table              │
│  • Apply filters                     │
│  • Return paginated results          │
└─────────────────────────────────────┘
```

---

## 🔑 Key Features

### 1. **Idempotency (Exactly Once Delivery)**
- **How**: `message_id` is PRIMARY KEY
- **Behavior**: 
  - First insert → Success
  - Duplicate insert → Caught by `IntegrityError` → Returns "duplicate"
- **Result**: Same message can be sent multiple times, but only stored once

### 2. **HMAC Signature Validation**
- **Algorithm**: HMAC-SHA256
- **Secret**: From `WEBHOOK_SECRET` env var
- **Header**: `X-Signature` (hex digest)
- **Security**: Constant-time comparison (`hmac.compare_digest`)

### 3. **Structured JSON Logging**
- **Format**: One JSON object per line
- **Fields**: `ts`, `level`, `request_id`, `method`, `path`, `status`, `latency_ms`
- **Webhook-specific**: `message_id`, `dup`, `result`
- **Benefits**: Easy to parse, search, and analyze

### 4. **Prometheus Metrics**
- **Format**: Prometheus exposition format (text/plain)
- **Metrics**: Counters and histograms with labels
- **Endpoint**: `GET /metrics`
- **Use Case**: Monitoring, alerting, dashboards

### 5. **12-Factor App Configuration**
- **Source**: Environment variables (`.env` file or system env)
- **No Hardcoding**: All secrets/configs from env
- **Validation**: Pydantic BaseSettings validates types

### 6. **Health Probes**
- **Liveness**: Always returns 200 (app is running)
- **Readiness**: Checks DB connectivity, table existence, config
- **Use Case**: Kubernetes/Docker health checks

### 7. **Pagination & Filtering**
- **Pagination**: `limit` and `offset` parameters
- **Total Count**: Always returns total matching records (ignores pagination)
- **Filters**: `from`, `since`, `q` (text search)
- **Ordering**: Deterministic (`ts ASC, message_id ASC`)

---

## 🐳 Docker Deployment

### Docker Compose Setup
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:////data/app.db
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
    volumes:
      - ./data:/data  # Persist database
```

### Startup Sequence
1. Container starts
2. `lifespan()` handler runs
3. `init_schema()` creates database
4. Uvicorn starts on port 8000
5. Application ready

---

## 📝 Example Request/Response Flows

### Example 1: Webhook Message Ingestion

**Request**:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <HMAC-SHA256-hex>" \
  -d '{
    "message_id": "msg-123",
    "from": "+919876543210",
    "to": "+1234567890",
    "ts": "2026-01-07T12:00:00Z",
    "text": "Hello, world!"
  }'
```

**Flow**:
1. Middleware generates `request_id`
2. Webhook endpoint reads body bytes
3. Verifies HMAC signature
4. Validates payload (Pydantic)
5. Inserts into database (idempotent)
6. Logs structured JSON
7. Records metrics
8. Returns `{"status": "ok"}`

**Response**:
```json
{"status": "ok"}
```

---

### Example 2: Message Retrieval

**Request**:
```bash
curl "http://localhost:8000/messages?from=%2B919876543210&limit=10&offset=0"
```

**Flow**:
1. Middleware generates `request_id`
2. Messages endpoint parses query params
3. Calls `list_messages()` with filters
4. Database queries with WHERE, ORDER BY, LIMIT, OFFSET
5. Returns paginated results + total count
6. Logs request
7. Records metrics

**Response**:
```json
{
  "data": [
    {
      "message_id": "msg-123",
      "from_msisdn": "+919876543210",
      "to_msisdn": "+1234567890",
      "ts": "2026-01-07T12:00:00Z",
      "text": "Hello, world!",
      "created_at": "2026-01-07T12:00:01Z"
    }
  ],
  "total": 150,
  "limit": 10,
  "offset": 0
}
```

---

## 🔍 Debugging Tips

1. **View Logs**: `docker compose logs api | grep '{"ts"' | sed 's/^[^|]*| //' | jq .`
2. **Check Metrics**: `curl http://localhost:8000/metrics`
3. **Health Check**: `curl http://localhost:8000/health/ready`
4. **Test Webhook**: Use correct `WEBHOOK_SECRET` for signature generation
5. **Database**: SQLite file at `/data/app.db` (in Docker) or `./data/app.db` (local)

---

## 📚 Summary

This FastAPI service is designed for **production use** with:
- ✅ Secure webhook ingestion (HMAC validation)
- ✅ Idempotent message storage (exactly once)
- ✅ Structured logging (JSON)
- ✅ Metrics (Prometheus)
- ✅ Health probes (Kubernetes-ready)
- ✅ 12-factor configuration
- ✅ Docker deployment

The architecture is **modular**, **testable**, and **scalable** (can be extended to use PostgreSQL, Redis, etc.).
