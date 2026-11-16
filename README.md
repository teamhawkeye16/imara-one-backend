# IMARA ONE Search — Backend Service (FastAPI & Fly.io)

Independent, privacy-first, intelligent search engine backend for the **IMARA ONE** cybersecurity ecosystem.

Powered by **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, and **Supabase Cloud PostgreSQL**.

---

## 1. Quick Deploy to Fly.io

### Step 1: Install Flyctl
If you don't have `flyctl` installed:
- **Windows (PowerShell)**:
  ```powershell
  iwr https://fly.io/install.ps1 -useb | iex
  ```
- **macOS / Linux**:
  ```bash
  curl -L https://fly.io/install.sh | sh
  ```

### Step 2: Login to Fly.io
```bash
fly auth login
```

### Step 3: Launch & Set Supabase Secrets
From the root of this repository:
```bash
# Initialize app without immediately deploying
fly launch --no-deploy --region syd

# Set your Supabase Database URL & secrets securely
fly secrets set DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require"
fly secrets set SUPABASE_URL="https://[PROJECT-REF].supabase.co"
fly secrets set SUPABASE_SECRET_KEY="your_supabase_secret_key_here"
fly secrets set SECRET_KEY="generate_a_random_64_character_hex_secret_here"
```

### Step 4: Deploy
```bash
fly deploy
```

Your API will be live globally at:
`https://imara-one-backend.fly.dev`

---

## 2. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Container & Supabase database healthcheck |
| `GET` | `/api/v1/search?q={query}` | Multi-engine web search with IMARA Shield & Instant Cards |
| `GET` | `/api/v1/search/suggest?q={prefix}` | Real-time search suggestions |
| `GET` | `/api/v1/stats` | Live index & privacy metrics |
| `GET` | `/api/v1/proxy/preview?url={url}` | Anonymized Zero-Trust Safe Reader viewer |
| `POST` | `/api/v1/crawler/submit` | Submit permitted domains for ingestion |

---

## 3. Local Development

```bash
# 1. Create virtualenv
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Architecture & Security
- **Zero-Trust Memory Processing**: Real-time search queries are processed in volatile memory without raw IP tracking.
- **SSRF Defense**: Enforces strict RFC 1918, link-local, loopback, and metadata address blocking.
- **IMARA Shield**: Real-time tracker detection and threat scoring (0-100%) on every outbound search hit.
