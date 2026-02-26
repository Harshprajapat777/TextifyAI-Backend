from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.services.file_service import (
    create_job,
    get_job,
    process_file,
    get_corrected_file_path,
)


router = APIRouter(tags=["Files"])

MAX_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # bytes


class UploadResponse(BaseModel):
    jobId: str
    status: str
    fileName: str


class StatusResponse(BaseModel):
    jobId: str
    status: str
    step: int
    totalSteps: int
    stepLabel: str


class CorrectionItem(BaseModel):
    original: str
    corrected: str
    line: int


class ReportResponse(BaseModel):
    jobId: str
    fileName: str
    totalWords: int
    totalErrors: int
    corrections: list[CorrectionItem]


@router.post("/files/upload", response_model=UploadResponse)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Create job and start background processing
    job_id = create_job(file.filename)
    background_tasks.add_task(process_file, job_id, file_bytes)

    return UploadResponse(jobId=job_id, status="processing", fileName=file.filename)


@router.get("/files/status/{job_id}", response_model=StatusResponse)
async def file_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatusResponse(
        jobId=job["jobId"],
        status=job["status"],
        step=job["step"],
        totalSteps=job["totalSteps"],
        stepLabel=job["stepLabel"],
    )


@router.get("/files/download/{job_id}")
async def download_file(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="File is not ready yet")

    path = get_corrected_file_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="Corrected file not found")

    corrected_name = job["fileName"].replace(".txt", "_corrected.txt")
    return FileResponse(
        path=str(path),
        filename=corrected_name,
        media_type="application/octet-stream",
    )


@router.get("/files/report/{job_id}", response_model=ReportResponse)
async def file_report(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="File is not ready yet")

    return ReportResponse(
        jobId=job["jobId"],
        fileName=job["fileName"],
        totalWords=job["totalWords"],
        totalErrors=job["totalErrors"],
        corrections=[
            CorrectionItem(
                original=c["original"],
                corrected=c["corrected"],
                line=c["line"],
            )
            for c in job["corrections"]
        ],
    )
