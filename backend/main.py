
import io
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pipeline import InsightEngine
from loaders import extract_video_id

load_dotenv()

app = FastAPI(title="InsightLens API", version="3.0.1")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
allow_origins = (
    ["*"]
    if frontend_origin == "*"
    else [origin.strip() for origin in frontend_origin.split(",") if origin.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=frontend_origin != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

ENGINES: dict[str, InsightEngine] = {}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))


class AskRequest(BaseModel):
    session_id: str = Field(min_length=10)
    question: str = Field(min_length=1, max_length=4000)


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=10)


class AddUrlsRequest(SessionRequest):
    urls: list[str] = Field(min_length=1, max_length=5)


def get_engine(session_id: str) -> InsightEngine:
    engine = ENGINES.get(session_id)
    if engine is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis session not found. Analyze a source again."
        )
    return engine


def run_analysis(factory):
    try:
        return factory()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/")
def root():
    return {"name": "InsightLens API", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/youtube")
def youtube_metadata(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL."
        )

    return {
        "video_id": video_id,
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "timestamp_url_example": f"https://www.youtube.com/watch?v={video_id}&t=60",
    }


@app.post("/api/analyze/url")
def analyze_url(url: str = Form(...)):
    session_id = uuid.uuid4().hex
    print("[PDF DEBUG] Creating InsightEngine", flush=True)
    engine = InsightEngine()
    print("[PDF DEBUG] InsightEngine created", flush=True)
    print("[PDF DEBUG] Starting PDF analysis", flush=True)
    result = run_analysis(lambda: engine.analyze_url(url.strip()))
    print("[PDF DEBUG] PDF analysis completed", flush=True)
    ENGINES[session_id] = engine
    result["session_id"] = session_id
    return result


@app.post("/api/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    import traceback

    print("[PDF DEBUG] Request received", flush=True)

    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Please upload a PDF file."
            )

        content = await file.read()
        print(f"[PDF DEBUG] File read: {len(content)} bytes", flush=True)
        await file.close()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty."
                )

        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"PDF is larger than {MAX_UPLOAD_MB} MB."
            )

        session_id = uuid.uuid4().hex
        engine = InsightEngine()

        print("[PDF DEBUG] Starting PDF analysis", flush=True)
        result = run_analysis(
            lambda: engine.analyze_pdf(content, file.filename)
        )
        print("[PDF DEBUG] PDF analysis completed", flush=True)

        ENGINES[session_id] = engine
        result["session_id"] = session_id

        print("[PDF DEBUG] Returning response", flush=True)
        return result

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="PDF analysis failed. Check the Render logs for details."
        )
    finally:
        await file.close()


@app.post("/api/add/url")
def add_url(request: AddUrlsRequest):
    engine = get_engine(request.session_id)
    result = engine.result()

    for url in request.urls:
        result = run_analysis(lambda url=url: engine.add_url(url.strip()))

    result["session_id"] = request.session_id
    return result


@app.post("/api/add/pdf")
async def add_pdf(session_id: str = Form(...), file: UploadFile = File(...)):
    engine = get_engine(session_id)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file."
        )

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"PDF is larger than {MAX_UPLOAD_MB} MB."
        )

    result = run_analysis(lambda: engine.add_pdf(content, file.filename))
    result["session_id"] = session_id
    return result


@app.post("/api/compare")
def compare(request: SessionRequest):
    engine = get_engine(request.session_id)
    return run_analysis(engine.compare)


@app.post("/api/ask")
def ask(request: AskRequest):
    engine = get_engine(request.session_id)
    return run_analysis(lambda: engine.ask(request.question))


@app.post("/api/export/pdf")
def export_pdf(session_id: str = Form(...)):
    engine = get_engine(session_id)
    pdf_bytes = run_analysis(engine.export_pdf)

    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes:
        raise HTTPException(
            status_code=500,
            detail="The report generator did not return valid PDF data."
        )

    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="InsightLens-Research-Report.pdf"'
        },
    )