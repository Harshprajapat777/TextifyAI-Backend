# TextifyAI

An AI-powered writing assistant with role-based workspaces, real-time spell-check, next-sentence predictions, and file correction.

---

## Frontend Stack

| Technology    | Version | Purpose                  |
| ------------- | ------- | ------------------------ |
| React         | 19.2.0  | UI framework             |
| Vite          | 7.3.1   | Build tool & dev server  |
| Tailwind CSS  | 4.1.18  | Utility-first styling    |
| Framer Motion | 12.34.0 | Animations & transitions |
| React Router  | 7.13.1  | Client-side routing      |
| Font Awesome  | 6.5.1   | Icon library (CDN)       |

## Current Features (Frontend Mock)

- **6 Role-Based Workspaces** — Lawyer, Doctor, Engineer, Faculty, Writer, Student
- **Real-Time Spell-Check** — Red wavy underlines with tap-to-correct popover
- **Next-Sentence Predictions** — Role-specific + generic prefix-based suggestion chips
- **AI Chat** — Mock conversation with typing indicator (1.5-3s simulated delay)
- **File Upload & Correction** — Upload `.txt` file, step-by-step analysis, download corrected file
- **Dark Theme** — Deep dark UI with role-specific gradient accents

---

## Backend Requirements

To move from frontend mocks to a production backend, the following services and infrastructure are needed.

### 1. API Framework

| Option      | Language | Why                                                          |
| ----------- | -------- | ------------------------------------------------------------ |
| **FastAPI** | Python   | Async support, auto-generated docs, great for ML integration |

**Recommended:** FastAPI — best fit for ML/NLP workloads with async file processing.

### 2. NLP & Spell-Check Service

Replace the 150-word mock dictionary with a production spell-checker.

| Library / Service        | Purpose                                                        |
| ------------------------ | -------------------------------------------------------------- |
| **SymSpell**             | Fastest spell-correction algorithm (million+ word dictionary)  |
| **pyspellchecker**       | Pure Python, Levenshtein distance-based                        |
| **language_tool_python** | Grammar + spelling (wraps LanguageTool)                        |
| **Hunspell**             | Industry-standard spell-checker (used by LibreOffice, Firefox) |
| TextBlob                 | Simple NLP with built-in spelling correction                   |

**Endpoints needed:**

```
POST /api/spellcheck
  Body: { "text": "teh recieve..." }
  Response: { "corrections": [{ "word": "teh", "suggestions": ["the"], "offset": 0 }] }
```

### 3. Prediction / Autocomplete Engine

Replace static prefix-matching with context-aware predictions.

| Approach         | Tool / Model                   | Notes                              |
| ---------------- | ------------------------------ | ---------------------------------- |
| **LLM-based**    | OpenAI GPT-4o / Claude API     | Best quality, role-aware prompting |
| On-device ML     | ONNX Runtime + distilled GPT-2 | Fast, no API cost, runs locally    |
| N-gram model     | KenLM / custom n-gram          | Lightweight, low latency           |
| Trie + frequency | Custom implementation          | Simplest, works for common phrases |

**Endpoints needed:**

```
POST /api/predict
  Body: { "text": "i want to", "role": "lawyer", "count": 5 }
  Response: { "predictions": ["I want to draft a contract", ...] }
```

### 4. AI Chat / Conversation Service

Replace mock random responses with real LLM integration.

| Provider          | Model                       | Use Case                              |
| ----------------- | --------------------------- | ------------------------------------- |
| **Anthropic**     | Claude (Sonnet/Haiku)       | Role-aware conversation, long context |
| OpenAI            | GPT-4o / GPT-4o-mini        | General-purpose chat                  |
| Google            | Gemini Pro                  | Multimodal capabilities               |
| Local/Self-hosted | Llama 3, Mistral via Ollama | Privacy-first, no API cost            |

**Endpoints needed:**

```
POST /api/chat
  Body: { "role": "doctor", "messages": [{ "sender": "user", "text": "..." }] }
  Response: { "reply": "Based on the symptoms described..." }

GET /api/chat/history/:conversationId
  Response: { "messages": [...] }
```

**Key considerations:**

- System prompts per role (e.g., "You are a legal writing assistant...")
- Conversation history / context window management
- Streaming responses via SSE or WebSocket for real-time typing effect

**Endpoints needed:**

```
POST /api/files/upload
  Body: multipart/form-data (file)
  Response: { "jobId": "abc123", "status": "processing" }

GET /api/files/status/:jobId
  Response: { "status": "analyzing", "step": 2, "totalSteps": 4 }

GET /api/files/download/:jobId
  Response: corrected file (application/octet-stream)

GET /api/files/report/:jobId
  Response: { "totalWords": 500, "errors": 12, "corrections": [...] }
```

**Why async?** Large files (10k+ words) take time. Use a job queue so the frontend can poll status and show step-by-step progress.

---

## requirements.txt

```txt
# ──── API Framework ────
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pydantic==2.10.0
pydantic-settings==2.6.0

# ──── NLP & Spell-Check ────
symspellpy==6.7.8
pyspellchecker==0.8.1
language-tool-python==2.9.0

# ──── AI / LLM Integration ────
anthropic==0.40.0               # Claude API
openai==1.55.0                  # OpenAI API (optional)
tiktoken==0.8.0                 # Token counting

# ──── Authentication ────
pyjwt==2.10.0
passlib[bcrypt]==1.7.4
python-jose==3.3.0

# ──── File Handling ────
python-docx==1.1.2              # .docx support (future)
pdfplumber==0.11.4              # .pdf support (future)
chardet==5.2.0                  # File encoding detection

# ──── Utilities ────
python-dotenv==1.0.1
httpx==0.28.0                   # Async HTTP client

# ──── Testing ────
pytest==8.3.0
pytest-asyncio==0.24.0

# ──── Development ────
ruff==0.8.0                     # Linter & formatter
```

---

## Quick Start (Frontend)

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # Production build -> dist/
```

## Backend Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your OpenAI API key

# Start the server
python -m uvicorn app.main:app --reload --port 8001
```

- **API:** http://localhost:8001
- **Swagger Docs:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

## Environment Variables

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
FRONTEND_URL=http://localhost:5173
```

---

## Backend Architecture (Proposed)

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # Settings from .env
│   ├── routes/                    # API endpoints
│   │   ├── auth.py                # Register, login, refresh
│   │   ├── chat.py                # Send message, get history
│   │   ├── spellcheck.py          # Check text, get corrections
│   │   ├── predict.py             # Get predictions for prefix
│   │   └── files.py               # Upload, status, download
│   ├── services/                  # Business logic
│   │   ├── nlp_service.py         # SymSpell + LanguageTool
│   │   ├── prediction_service.py
│   │   ├── llm_service.py         # Claude / OpenAI integration
│   │   └── file_service.py        # File processing pipeline
│   └── middleware/
│       └── auth.py                # JWT verification
├── tests/
├── requirements.txt
└── .env.example
```
