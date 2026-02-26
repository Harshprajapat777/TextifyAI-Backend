# TextifyAI Backend — Development Plan

> **Stack:** FastAPI + OpenAI | No Auth | No Database | Pure Stateless API

---

## Stage 1: Foundation + Spell Check + Predictions

### Goal

Get a running FastAPI server with spell-check and role-aware next-sentence predictions.

### Endpoints

#### `POST /api/spellcheck`

```json
// Request
{
  "text": "teh recieve definately"
}

// Response
{
  "corrections": [
    { "word": "teh", "suggestions": ["the"], "offset": 0 },
    { "word": "recieve", "suggestions": ["receive"], "offset": 4 },
    { "word": "definately", "suggestions": ["definitely"], "offset": 12 }
  ]
}
```

- Uses **SymSpell** (offline, no API cost, fastest spell-correction algorithm)
- Returns word, suggestions list, and character offset

#### `POST /api/predict`

```json
// Request
{
  "text": "I want to",
  "role": "lawyer",
  "count": 5
}

// Response
{
  "predictions": [
    "I want to draft a contract for the client",
    "I want to file a motion in court",
    "I want to review the terms of the agreement",
    "I want to schedule a deposition",
    "I want to request an extension on the deadline"
  ]
}
```

- Uses **OpenAI GPT-4o** with role-specific system prompts
- `role` must be one of: `lawyer`, `doctor`, `engineer`, `faculty`, `writer`, `student`
- `count` controls how many predictions to return (default: 5)

### Files to Create

```
app/
├── main.py                  # FastAPI app, CORS, startup
├── config.py                # Settings from .env (OPENAI_API_KEY, CORS, etc.)
├── routes/
│   ├── spellcheck.py        # POST /api/spellcheck
│   └── predict.py           # POST /api/predict
├── services/
│   ├── nlp_service.py       # SymSpell initialization + spell-check logic
│   └── llm_service.py       # OpenAI client + role system prompts
.env.example
requirements.txt
```

### Dependencies (Stage 1)

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pydantic==2.10.0
pydantic-settings==2.6.0
symspellpy==6.7.8
openai==1.55.0
python-dotenv==1.0.1
httpx==0.28.0
```

### Environment Variables (Stage 1)

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
FRONTEND_URL=http://localhost:5173
```

---

## Stage 2: AI Chat with Streaming

### Goal

Add real LLM-powered chat with per-role system prompts and SSE streaming for real-time typing effect.

### Endpoints

#### `POST /api/chat`

```json
// Request
{
  "role": "doctor",
  "messages": [
    { "sender": "user", "text": "What are common symptoms of iron deficiency?" }
  ]
}

// Response (non-streaming)
{
  "reply": "Common symptoms of iron deficiency include fatigue, pale skin, shortness of breath..."
}
```

#### `POST /api/chat/stream`

```json
// Request (same as /api/chat)
{
  "role": "doctor",
  "messages": [
    { "sender": "user", "text": "What are common symptoms of iron deficiency?" }
  ]
}

// Response: Server-Sent Events (SSE)
// Content-Type: text/event-stream
data: {"token": "Common"}
data: {"token": " symptoms"}
data: {"token": " of"}
data: {"token": " iron"}
...
data: {"done": true}
```

- Uses **OpenAI GPT-4o** with streaming enabled
- Frontend sends full conversation history each request (no server-side storage)
- SSE stream for real-time token-by-token typing effect

### Role System Prompts

| Role       | System Prompt Summary                                               |
| ---------- | ------------------------------------------------------------------- |
| `lawyer`   | You are a legal writing assistant. Help with contracts, briefs...   |
| `doctor`   | You are a medical writing assistant. Help with clinical notes...    |
| `engineer` | You are a technical writing assistant. Help with documentation...   |
| `faculty`  | You are an academic writing assistant. Help with papers, syllabi... |
| `writer`   | You are a creative writing assistant. Help with stories, prose...   |
| `student`  | You are a study assistant. Help with essays, assignments...         |

### Files to Create / Update

```
app/
├── routes/
│   └── chat.py              # POST /api/chat + POST /api/chat/stream
├── services/
│   └── llm_service.py       # (update) Add chat + streaming methods
```

### Dependencies Added (Stage 2)

```txt
sse-starlette==2.1.0         # SSE support for FastAPI
```

---

## Stage 3: File Upload & Correction

### Goal

Upload a `.txt` file, run spell + grammar correction on the server, track progress, download the corrected file and a report.

### Endpoints

#### `POST /api/files/upload`

```
Content-Type: multipart/form-data
Body: file (.txt)

// Response
{
  "jobId": "abc123",
  "status": "processing",
  "fileName": "essay.txt"
}
```

#### `GET /api/files/status/{jobId}`

```json
// Response
{
  "jobId": "abc123",
  "status": "analyzing",       // queued | analyzing | correcting | completed | failed
  "step": 2,
  "totalSteps": 4,
  "stepLabel": "Running spell check..."
}
```

**Processing Steps:**

| Step | Label                       |
| ---- | --------------------------- |
| 1    | Reading and parsing file    |
| 2    | Running spell check         |
| 3    | Applying corrections        |
| 4    | Generating report           |

#### `GET /api/files/download/{jobId}`

```
Response: corrected file (application/octet-stream)
Content-Disposition: attachment; filename="essay_corrected.txt"
```

#### `GET /api/files/report/{jobId}`

```json
{
  "jobId": "abc123",
  "fileName": "essay.txt",
  "totalWords": 500,
  "totalErrors": 12,
  "corrections": [
    { "original": "teh", "corrected": "the", "line": 3 },
    { "original": "recieve", "corrected": "receive", "line": 7 }
  ]
}
```

### Architecture

- **In-memory job tracking** — Python dict `{jobId: JobStatus}` (no database)
- **Local file storage** — `uploads/` directory for original + corrected files
- **Background processing** — FastAPI `BackgroundTasks` for async file correction
- **SymSpell** for spell correction (reuses `nlp_service.py` from Stage 1)

### Files to Create / Update

```
app/
├── routes/
│   └── files.py             # Upload, status, download, report endpoints
├── services/
│   └── file_service.py      # File processing pipeline + in-memory job store
uploads/                     # Created at runtime (gitignored)
```

### Dependencies Added (Stage 3)

```txt
chardet==5.2.0               # File encoding detection
```

### Config Added (Stage 3)

```env
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10
```

---

## Final Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, startup, lifespan
│   ├── config.py                  # Pydantic settings from .env
│   ├── routes/
│   │   ├── spellcheck.py          # Stage 1
│   │   ├── predict.py             # Stage 1
│   │   ├── chat.py                # Stage 2
│   │   └── files.py               # Stage 3
│   └── services/
│       ├── nlp_service.py         # Stage 1 — SymSpell spell-check
│       ├── llm_service.py         # Stage 1+2 — OpenAI predictions + chat
│       └── file_service.py        # Stage 3 — File processing pipeline
├── uploads/                       # Runtime file storage (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
├── start.md                       # This file
└── readme.md
```

## Full requirements.txt

```txt
# ──── API Framework ────
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pydantic==2.10.0
pydantic-settings==2.6.0

# ──── NLP & Spell-Check ────
symspellpy==6.7.8

# ──── AI / LLM Integration ────
openai==1.55.0
tiktoken==0.8.0

# ──── Streaming ────
sse-starlette==2.1.0

# ──── File Handling ────
chardet==5.2.0

# ──── Utilities ────
python-dotenv==1.0.1
httpx==0.28.0
```

## Full .env.example

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
FRONTEND_URL=http://localhost:5173
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10
```

## How to Run

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate         # Linux/Mac
venv\Scripts\activate            # Windows

# Install dependencies
pip install -r requirements.txt

# Setup env
cp .env.example .env
# Edit .env with your OpenAI API key

# Start server
uvicorn app.main:app --reload --port 8000

# API docs available at
# http://localhost:8000/docs
```
