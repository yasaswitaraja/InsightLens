# InsightLens 2.0 — Production Web Architecture

InsightLens is now split into:

- `frontend/` — React + Vite UI for Vercel
- `backend/` — FastAPI + LangChain RAG API for Render

## What was fixed

1. Replaced the Streamlit-only UI with a real React interface.
2. Dark black ChatGPT-style workspace.
3. Orange action buttons without purple gradients.
4. YouTube URLs support:
   - `youtube.com/watch?v=...`
   - `youtu.be/...`
   - `/shorts/...`
   - `/embed/...`
   - `/live/...`
5. YouTube video is rendered with `youtube-nocookie.com` embed.
6. Direct "Open in YouTube" fallback is always shown.
7. Transcript loading checks English, common Indian-language captions, and then any available caption track.
8. PDF upload and extraction.
9. Grounded RAG Q&A.
10. Full PDF report export including source metadata, summary, insights, and Q&A history.
11. FastAPI CORS configuration for the Vercel frontend.
12. `/health` endpoint for Render.
13. No API keys are placed in the frontend.

## Important architecture note

The old repository was a Streamlit application. Vercel should host the new `frontend/` directory, while Render hosts `backend/`.

The backend keeps an in-memory analysis session. This is appropriate for a single-instance demo deployment, but if you later scale to multiple backend instances, move sessions/vector stores to a persistent shared store.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
```

Fill in:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
FRONTEND_ORIGIN=http://localhost:5173
```

Start:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
```

Set:

```env
VITE_API_URL=http://localhost:8000
```

Start:

```bash
npm run dev
```

## Render deployment

Create a Render Web Service using the `backend/` directory.

Build:

```bash
pip install -r requirements.txt
```

Start:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Health check:

```text
/health
```

Environment variables:

```env
GROQ_API_KEY=...
GEMINI_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
FRONTEND_ORIGIN=https://YOUR-VERCEL-DOMAIN.vercel.app
MAX_UPLOAD_MB=20
```

## Vercel deployment

Import the repository into Vercel and set the project root to:

```text
frontend
```

Build command:

```bash
npm run build
```

Output directory:

```text
dist
```

Environment variable:

```env
VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

After the Vercel domain is known, update Render's `FRONTEND_ORIGIN` to that exact Vercel origin and redeploy the backend.

## YouTube limitation

The application separates video playback from transcript extraction.

A valid YouTube URL can always produce a YouTube watch URL and embed URL. AI analysis still requires an accessible YouTube caption/transcript. Some videos disable captions or restrict transcript access; those videos cannot be reliably analyzed by the public transcript API without an additional transcription provider.

The current loader follows the documented `youtube-transcript-api` API and tries multiple languages/caption tracks.

## API endpoints

- `GET /health`
- `GET /api/youtube?url=...`
- `POST /api/analyze/url`
- `POST /api/analyze/pdf`
- `POST /api/ask`
- `POST /api/export/pdf`
