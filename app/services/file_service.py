import csv
import io
import uuid
import asyncio
from pathlib import Path

import chardet
import pypdf

from app.config import settings
from app.services.nlp_service import nlp_service

# In-memory job store (no database)
_jobs: dict[str, dict] = {}

STEPS = [
    "Reading and parsing file",
    "Running spell check",
    "Applying corrections",
    "Generating report",
]


def _get_upload_dir() -> Path:
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_job(filename: str) -> str:
    """Create a new processing job and return its ID."""
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "jobId": job_id,
        "fileName": filename,
        "status": "queued",
        "step": 0,
        "totalSteps": len(STEPS),
        "stepLabel": "",
        "totalWords": 0,
        "totalErrors": 0,
        "corrections": [],
    }
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _update_step(job_id: str, step: int, status: str = "processing"):
    job = _jobs[job_id]
    job["step"] = step
    job["status"] = status
    job["stepLabel"] = STEPS[step - 1] if 1 <= step <= len(STEPS) else ""


def _extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from .txt, .pdf, or .csv files."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )

    if ext == ".csv":
        detected = chardet.detect(file_bytes)
        encoding = detected.get("encoding") or "utf-8"
        text = file_bytes.decode(encoding, errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join(" ".join(row) for row in reader)

    # Default: plain text
    detected = chardet.detect(file_bytes)
    encoding = detected.get("encoding") or "utf-8"
    return file_bytes.decode(encoding, errors="replace")


async def process_file(job_id: str, file_bytes: bytes):
    """Run the full spell-check pipeline in the background."""
    upload_dir = _get_upload_dir()

    try:
        # Step 1: Read and parse file
        _update_step(job_id, 1, "analyzing")
        await asyncio.sleep(0.3)

        job = _jobs[job_id]
        text = _extract_text(file_bytes, job["fileName"])
        lines = text.splitlines()
        job["totalWords"] = len(text.split())

        # Save original as txt
        original_path = upload_dir / f"{job_id}_original.txt"
        original_path.write_text(text, encoding="utf-8")

        # Step 2: Run spell check
        _update_step(job_id, 2)
        await asyncio.sleep(0.2)

        corrections = []
        for line_num, line in enumerate(lines, start=1):
            for c in nlp_service.check_text(line):
                corrections.append({
                    "original": c["word"],
                    "corrected": c["correction"],
                    "line": line_num,
                })

        job["totalErrors"] = len(corrections)
        job["corrections"] = corrections

        # Step 3: Apply corrections
        _update_step(job_id, 3, "correcting")
        await asyncio.sleep(0.2)

        for line_num, line in enumerate(lines, start=1):
            line_corrections = nlp_service.check_text(line)
            for c in sorted(line_corrections, key=lambda x: x["offset"], reverse=True):
                start = c["offset"]
                end = start + c["length"]
                line = line[:start] + c["correction"] + line[end:]
            lines[line_num - 1] = line

        corrected_text = "\n".join(lines)

        # Save corrected file
        corrected_path = upload_dir / f"{job_id}_corrected.txt"
        corrected_path.write_text(corrected_text, encoding="utf-8")

        # Step 4: Generate report
        _update_step(job_id, 4)
        await asyncio.sleep(0.1)

        job["status"] = "completed"
        job["stepLabel"] = "Done"

    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["stepLabel"] = str(e)


def get_corrected_file_path(job_id: str) -> Path | None:
    path = _get_upload_dir() / f"{job_id}_corrected.txt"
    return path if path.exists() else None
