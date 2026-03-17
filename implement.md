# TextifyAI — Frontend Integration Guide

> **Base URL:** `http://localhost:8001`
> **Swagger Docs:** `http://localhost:8001/docs`
> **ReDoc:** `http://localhost:8001/redoc`

---

## Setup

```js
// src/api/client.js (or wherever you keep API helpers)
const API_BASE = "http://localhost:8001/api";

async function api(endpoint, body) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "API error");
  }
  return res.json();
}

export { api, API_BASE };
```

---

## Available Roles

Used across all role-aware endpoints. Pass one of these as the `role` field:

```js
const ROLES = ["lawyer", "doctor", "engineer", "faculty", "writer", "student"];
```

---

## Stage 1 — Live Now

### 1. Spell Check

**`POST /api/spellcheck`**

Checks text for spelling errors using SymSpell (offline, no API cost, instant).

#### Request

```js
const data = await api("/spellcheck", {
  text: "teh recieve definately"
});
```

| Field  | Type     | Required | Description         |
| ------ | -------- | -------- | ------------------- |
| `text` | `string` | Yes      | Text to spell-check |

#### Response

```json
{
  "corrections": [
    {
      "word": "teh",
      "correction": "The",
      "offset": 0,
      "length": 3
    },
    {
      "word": "recieve",
      "correction": "receive",
      "offset": 4,
      "length": 7
    },
    {
      "word": "definately",
      "correction": "definitely",
      "offset": 12,
      "length": 10
    }
  ],
  "auto_corrected_text": "The receive definitely"
}
```

| Field                       | Type     | Description                                         |
| --------------------------- | -------- | --------------------------------------------------- |
| `corrections`               | `array`  | List of misspelled words (empty if no errors found) |
| `corrections[].word`        | `string` | The misspelled word                                 |
| `corrections[].correction`  | `string` | Single best correction                              |
| `corrections[].offset`      | `number` | Character offset in the original text               |
| `corrections[].length`      | `number` | Length of the misspelled word (for underline span)  |
| `auto_corrected_text`       | `string` | Full text with all corrections applied              |

#### Frontend Usage Example

```jsx
// Real-time spell check on typing (debounce 300ms)
const checkSpelling = async (text) => {
  const { corrections, auto_corrected_text } = await api("/spellcheck", { text });

  if (corrections.length === 0) {
    // No errors — clear any existing highlights
    return;
  }

  // 1. Highlight misspelled words using offset + length
  //    Render a red underline over text[offset : offset + length] for each correction
  highlightMisspelledWords(text, corrections);

  // 2. Auto-fix: update the editor content with the corrected text
  setEditorText(auto_corrected_text);
};

// Example: build highlight spans from corrections
const highlightMisspelledWords = (text, corrections) => {
  // corrections are sorted by offset so you can build spans in order
  corrections.forEach(({ word, correction, offset, length }) => {
    // Mark text[offset : offset + length] with a red underline
    // Show a tooltip/chip with `correction` value on hover or tap
  });
};
```

---

### 2. Next-Sentence Predictions

**`POST /api/predict`**

Generates role-aware sentence completions using OpenAI GPT-4o.

#### Request

```js
const data = await api("/predict", {
  text: "I want to",
  role: "lawyer",
  count: 5
});
```

| Field   | Type     | Required | Default     | Description                        |
| ------- | -------- | -------- | ----------- | ---------------------------------- |
| `text`  | `string` | Yes      | —           | Partial text to complete           |
| `role`  | `string` | No       | `"student"` | One of the 6 roles                 |
| `count` | `number` | No       | `5`         | Number of predictions (1-10)       |

#### Response

```json
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

| Field         | Type       | Description                          |
| ------------- | ---------- | ------------------------------------ |
| `predictions` | `string[]` | Array of completed sentence options  |

#### Frontend Usage Example

```jsx
// Trigger predictions only when user has typed at least 4 words
// The backend enforces this too — returns [] for fewer than 4 words
const getPredictions = async (text, role) => {
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  if (wordCount < 4) return []; // skip — not enough words yet
  const { predictions } = await api("/predict", { text, role, count: 5 });
  return predictions;
};

// Render predictions as a vertical list below the editor (not inline chips)
// Example JSX:
// <ul className="prediction-list">
//   {predictions.map((p, i) => (
//     <li key={i} onClick={() => setEditorText(p)} className="prediction-item">
//       {p}
//     </li>
//   ))}
// </ul>
//
// On click → replace/set editor text with the selected prediction
```

---

## Stage 2 — AI Chat (Coming Next)

### 3. Chat (Request/Response)

**`POST /api/chat`**

#### Request

```js
const data = await api("/chat", {
  role: "doctor",
  messages: [
    { sender: "user", text: "What are common symptoms of iron deficiency?" }
  ]
});
```

| Field      | Type     | Required | Default     | Description                         |
| ---------- | -------- | -------- | ----------- | ----------------------------------- |
| `role`     | `string` | No       | `"student"` | One of the 6 roles                  |
| `messages` | `array`  | Yes      | —           | Conversation history                |
| `messages[].sender` | `string` | Yes | —      | `"user"` or `"assistant"`           |
| `messages[].text`   | `string` | Yes | —      | Message content                     |

#### Response

```json
{
  "reply": "Common symptoms of iron deficiency include fatigue, pale skin..."
}
```

### 4. Chat Streaming (SSE)

**`POST /api/chat/stream`**

Same request body as `/api/chat`. Returns structured Server-Sent Events — first a short description, then numbered points one by one.

#### SSE Event Types

The backend automatically detects whether the message is casual or informational and picks the right format.

**Casual messages** (greetings, small talk):

| Event     | Data shape              | When        |
| --------- | ----------------------- | ----------- |
| `message` | `{ "text": "..." }`     | Single reply|
| `done`    | `{}`                    | Last event  |

**Informational questions:**

| Event         | Data shape                         | When           |
| ------------- | ---------------------------------- | -------------- |
| `description` | `{ "text": "One-line overview." }` | First event    |
| `point`       | `{ "index": 1, "text": "..." }`    | Once per point |
| `done`        | `{}`                               | Last event     |

#### Raw SSE Stream Examples

Casual:
```
event: message
data: {"text": "Hello! How can I help you today?"}

event: done
data: {}
```

Informational:
```
event: description
data: {"text": "Iron deficiency causes several notable physical symptoms."}

event: point
data: {"index": 1, "text": "Persistent fatigue and low energy levels."}

event: point
data: {"index": 2, "text": "Pale or yellowish skin tone."}

event: point
data: {"index": 3, "text": "Shortness of breath during mild activity."}

event: done
data: {}
```

#### Frontend Usage Example

```js
const streamChat = async (role, messages, handlers) => {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, messages }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        if (currentEvent === "message")     handlers.onMessage(data.text);
        if (currentEvent === "description") handlers.onDescription(data.text);
        if (currentEvent === "point")       handlers.onPoint(data.index, data.text);
        if (currentEvent === "done")        handlers.onDone();
      }
    }
  }
};

// Usage
streamChat("doctor", messages, {
  onMessage:     (text) => setChatReply(text),               // casual reply
  onDescription: (text) => setDescription(text),             // informational
  onPoint:       (index, text) => setPoints(prev => [...prev, { index, text }]),
  onDone:        () => setStreaming(false),
});
```

---

## Stage 3 — File Upload & Correction (Coming Later)

### 5. Upload File

**`POST /api/files/upload`** — `multipart/form-data`

```js
const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    body: formData,
  });
  return res.json();
  // → { jobId: "abc123", status: "processing", fileName: "essay.txt" }
};
```

### 6. Poll Job Status

**`GET /api/files/status/{jobId}`**

```js
const pollStatus = async (jobId) => {
  const res = await fetch(`${API_BASE}/files/status/${jobId}`);
  return res.json();
  // → { jobId, status: "analyzing", step: 2, totalSteps: 4, stepLabel: "Running spell check..." }
};

// Poll every 1.5s until status === "completed"
```

| Status        | Meaning                  |
| ------------- | ------------------------ |
| `queued`      | Waiting to be processed  |
| `analyzing`   | Reading and parsing file |
| `correcting`  | Applying corrections     |
| `completed`   | Done, ready to download  |
| `failed`      | Error during processing  |

### 7. Download Corrected File

**`GET /api/files/download/{jobId}`**

```js
const downloadFile = async (jobId) => {
  const res = await fetch(`${API_BASE}/files/download/${jobId}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  // trigger download
  const a = document.createElement("a");
  a.href = url;
  a.download = "corrected.txt";
  a.click();
};
```

### 8. Get Correction Report

**`GET /api/files/report/{jobId}`**

```js
const getReport = async (jobId) => {
  const res = await fetch(`${API_BASE}/files/report/${jobId}`);
  return res.json();
  // → { jobId, fileName, totalWords: 500, totalErrors: 12, corrections: [...] }
};
```

---

## Error Handling

All endpoints return errors in this format:

```json
{
  "detail": "Invalid role 'chef'. Must be one of: ['lawyer', 'doctor', 'engineer', 'faculty', 'writer', 'student']"
}
```

| Status Code | Meaning                                  |
| ----------- | ---------------------------------------- |
| `200`       | Success                                  |
| `400`       | Bad request (invalid role, missing field) |
| `422`       | Validation error (wrong types)           |
| `500`       | Server error                             |

```js
// Generic error handler
try {
  const data = await api("/spellcheck", { text });
} catch (err) {
  console.error("API Error:", err.message);
  // show toast / notification to user
}
```

---

## Quick Reference

| # | Method | Endpoint                    | Stage | Cost    |
|---|--------|-----------------------------|-------|---------|
| 1 | POST   | `/api/spellcheck`           | 1     | Free    |
| 2 | POST   | `/api/predict`              | 1     | OpenAI  |
| 3 | POST   | `/api/chat`                 | 2     | OpenAI  |
| 4 | POST   | `/api/chat/stream`          | 2     | OpenAI  |
| 5 | POST   | `/api/files/upload`         | 3     | Free    |
| 6 | GET    | `/api/files/status/{jobId}` | 3     | Free    |
| 7 | GET    | `/api/files/download/{jobId}` | 3   | Free    |
| 8 | GET    | `/api/files/report/{jobId}` | 3     | Free    |
