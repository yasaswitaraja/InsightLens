
import io
import os
import uuid
import traceback
from typing import Callable, TypeVar

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pipeline import InsightEngine
from loaders import extract_video_id


load_dotenv()


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="InsightLens API",
    version="3.0.2",
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")

allow_origins = (
    ["*"]
    if frontend_origin.strip() == "*"
    else [
        origin.strip().rstrip("/")
        for origin in frontend_origin.split(",")
        if origin.strip()
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=frontend_origin.strip() != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CONFIGURATION AND SESSION STORAGE
# ============================================================

ENGINES: dict[str, InsightEngine] = {}

try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
except ValueError:
    MAX_UPLOAD_MB = 20

if MAX_UPLOAD_MB < 1:
    MAX_UPLOAD_MB = 20

T = TypeVar("T")


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):
    session_id: str = Field(min_length=10)
    question: str = Field(min_length=1, max_length=4000)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=10)


class AddUrlsRequest(SessionRequest):
    urls: list[str] = Field(min_length=1, max_length=5)


# ============================================================
# COMMON HELPERS
# ============================================================

def get_engine(session_id: str) -> InsightEngine:
    engine = ENGINES.get(session_id)

    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis session not found. "
                "Please analyze a source again."
            ),
        )

    return engine


def run_analysis(factory: Callable[[], T]) -> T:
    """Run an analysis operation and log its actual failure."""

    try:
        return factory()

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"[ANALYSIS ERROR] {type(exc).__name__}: {exc}",
            flush=True,
        )
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "Analysis failed. "
                "Check the backend logs for details."
            ),
        ) from exc


async def read_upload(
    file: UploadFile,
    allowed_extensions: tuple[str, ...],
    file_description: str,
) -> bytes:
    """Validate and read an uploaded file."""

    filename = file.filename or ""

    if not filename:
        raise HTTPException(
            status_code=400,
            detail=f"No {file_description} file was uploaded.",
        )

    if not filename.lower().endswith(allowed_extensions):
        allowed = ", ".join(allowed_extensions)

        raise HTTPException(
            status_code=400,
            detail=f"Supported file extensions: {allowed}.",
        )

    try:
        # Read at most one byte beyond the configured limit so
        # oversized files can be rejected without loading them fully.
        content = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)

    finally:
        await file.close()

    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"The uploaded {file_description} file is empty.",
        )

    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=(
                f"The {file_description} file exceeds "
                f"the {MAX_UPLOAD_MB} MB upload limit."
            ),
        )

    return content


def save_session(
    session_id: str,
    engine: InsightEngine,
    result: dict,
) -> dict:
    """Store an engine and attach its session ID to the response."""

    ENGINES[session_id] = engine
    result["session_id"] = session_id

    return result


# ============================================================
# ROOT AND HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "name": "InsightLens API",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# YOUTUBE METADATA
# ============================================================

@app.get("/api/youtube")
def youtube_metadata(url: str):
    video_id = extract_video_id(url)

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL.",
        )

    return {
        "video_id": video_id,
        "watch_url": (
            f"https://www.youtube.com/watch?v={video_id}"
        ),
        "embed_url": (
            "https://www.youtube-nocookie.com/embed/"
            f"{video_id}"
        ),
        "thumbnail_url": (
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        ),
        "timestamp_url_example": (
            f"https://www.youtube.com/watch?v={video_id}&t=60"
        ),
    }


# ============================================================
# ANALYZE WEBPAGE URL
# ============================================================

@app.post("/api/analyze/url")
def analyze_url(url: str = Form(...)):
    cleaned_url = url.strip()

    if not cleaned_url:
        raise HTTPException(
            status_code=400,
            detail="URL cannot be empty.",
        )

    session_id = uuid.uuid4().hex

    print("[URL DEBUG] Creating InsightEngine", flush=True)

    engine = InsightEngine()

    print("[URL DEBUG] Starting URL analysis", flush=True)

    result = run_analysis(
        lambda: engine.analyze_url(cleaned_url)
    )

    print("[URL DEBUG] URL analysis completed", flush=True)

    return save_session(session_id, engine, result)


# ============================================================
# ANALYZE PDF
# ============================================================

@app.post("/api/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    print("[PDF DEBUG] Request received", flush=True)

    try:
        filename = file.filename or ""

        content = await read_upload(
            file,
            (".pdf",),
            "PDF",
        )

        print(
            f"[PDF DEBUG] File read: {len(content)} bytes",
            flush=True,
        )

        session_id = uuid.uuid4().hex
        engine = InsightEngine()

        print(
            "[PDF DEBUG] Starting PDF analysis",
            flush=True,
        )

        result = run_analysis(
            lambda: engine.analyze_pdf(content, filename)
        )

        print(
            "[PDF DEBUG] PDF analysis completed",
            flush=True,
        )

        response = save_session(session_id, engine, result)

        print(
            "[PDF DEBUG] Returning response",
            flush=True,
        )

        return response

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"[PDF ERROR] {type(exc).__name__}: {exc}",
            flush=True,
        )
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "PDF analysis failed. "
                "Check the backend logs for details."
            ),
        ) from exc

    finally:
            await file.close()


# ============================================================
# ANALYZE UPLOADED TXT OR SRT TRANSCRIPT
# ============================================================

@app.post("/api/analyze/transcript")
async def analyze_transcript(file: UploadFile = File(...)):
    filename = file.filename or ""

    content = await read_upload(
        file,
        (".txt", ".srt"),
        "transcript",
    )

    session_id = uuid.uuid4().hex
    engine = InsightEngine()

    result = run_analysis(
        lambda: engine.analyze_transcript(content, filename)
    )

    return save_session(session_id, engine, result)


# ============================================================
# ADD WEBPAGE URLS TO AN EXISTING SESSION
# ============================================================

@app.post("/api/add/url")
def add_url(request: AddUrlsRequest):
    engine = get_engine(request.session_id)

    result = engine.result()

    for url in request.urls:
        cleaned_url = url.strip()

        if not cleaned_url:
            raise HTTPException(
                status_code=400,
                detail="An additional URL cannot be empty.",
            )

        result = run_analysis(
            lambda cleaned_url=cleaned_url: engine.add_url(
                cleaned_url
            )
        )

    result["session_id"] = request.session_id

    return result


# ============================================================
# ADD PDF TO AN EXISTING SESSION
# ============================================================

@app.post("/api/add/pdf")
async def add_pdf(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    engine = get_engine(session_id)
    filename = file.filename or ""

    content = await read_upload(
        file,
        (".pdf",),
        "PDF",
    )

    result = run_analysis(
        lambda: engine.add_pdf(content, filename)
    )

    result["session_id"] = session_id

    return result


# ============================================================
# ADD TXT OR SRT TRANSCRIPT TO AN EXISTING SESSION
# ============================================================

@app.post("/api/add/transcript")
async def add_transcript(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    engine = get_engine(session_id)
    filename = file.filename or ""

    content = await read_upload(
        file,
        (".txt", ".srt"),
        "transcript",
    )

    result = run_analysis(
        lambda: engine.add_transcript(content, filename)
    )

    result["session_id"] = session_id

    return result


# ============================================================
# COMPARE SOURCES IN AN EXISTING SESSION
# ============================================================

@app.post("/api/compare")
def compare(request: SessionRequest):
    engine = get_engine(request.session_id)

    return run_analysis(engine.compare)


# ============================================================
# ASK A QUESTION ABOUT THE ANALYZED SOURCE
# ============================================================

@app.post("/api/ask")
def ask(request: AskRequest):
    engine = get_engine(request.session_id)

    return run_analysis(
        lambda: engine.ask(request.question.strip())
    )


# ============================================================
# EXPORT ANALYSIS AS A PDF REPORT
# ============================================================

@app.post("/api/export/pdf")
def export_pdf(session_id: str = Form(...)):
    engine = get_engine(session_id)

    pdf_bytes = run_analysis(engine.export_pdf)

    if (
        not isinstance(pdf_bytes, (bytes, bytearray))
        or not pdf_bytes
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "The report generator did not return "
                "valid PDF data."
            ),
        )

    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="InsightLens-Research-Report.pdf"'
            ),
        },
    )
