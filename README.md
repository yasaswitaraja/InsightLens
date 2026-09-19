# Multi-Source Insight & Q&A Generator

Takes a **YouTube video**, **research paper (PDF/arXiv)**, or **web article**, and produces:
- A structured summary (key points, claims + evidence, limitations, target audience)
- Auto-generated Q&A grounded in the source
- An interactive chat interface with citations
- A basic **groundedness eval** (LLM-as-judge hallucination check)

Built with LangChain, OpenAI, Chroma, and Streamlit.

## Architecture

```
URL input
   │
   ▼
┌─────────────┐     detect source type (youtube / pdf / web)
│  loaders.py │ ──► extract raw text + metadata
└─────────────┘     (transcript API / pypdf / BeautifulSoup)
   │
   ▼
┌─────────────┐     source-aware chunking
│ pipeline.py │ ──► OpenAI embeddings → Chroma vector store
└─────────────┘     map-reduce summarization (Pydantic structured output)
   │                retrieval-grounded Q&A generation
   ▼
┌─────────────┐
│ qa_eval.py  │ ──► LLM-as-judge groundedness check on generated Q&A
└─────────────┘
   │
   ▼
┌─────────────┐
│   app.py    │ ──► Streamlit UI (summary / Q&A / chat / eval tabs)
└─────────────┘
```

## Design decisions worth knowing for an interview

- **Chunking strategy differs by source type.** YouTube transcripts are conversational,
  so they use smaller chunks (800 chars) with more overlap to preserve context around a
  spoken idea. Papers use larger chunks (1200 chars) since paragraphs are denser and more
  self-contained. This is a deliberate tradeoff, not a default.
- **Map-reduce summarization** instead of stuffing the whole document into one prompt —
  avoids context-window blowups on long transcripts/papers and is cheaper per call.
- **Structured output via Pydantic** (`PydanticOutputParser`) rather than asking the LLM
  to "return JSON" and hoping — this fails loudly and predictably instead of silently
  producing malformed output.
- **Citations are enforced by prompt design**, not post-hoc: the QA chain is given
  numbered context blocks and instructed to cite `[1]`, `[2]`, etc., and told explicitly
  to say "not found" rather than guess.
- **The eval is real, if simple**: an LLM-as-judge pass checks whether each auto-generated
  answer is actually supported by the source text, and reports a pass rate. Most portfolio
  RAG projects skip evaluation entirely — this one doesn't.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your OpenAI API key
streamlit run app.py
```

## Known limitations

- Uses an in-memory Chroma store — data doesn't persist between runs. For a production
  version, add a `persist_directory` and reuse the vector store across sessions.
- YouTube extraction depends on the video having captions/transcripts enabled.
- The groundedness eval is LLM-as-judge, not a formal metric (e.g. RAGAS) — good enough
  to demonstrate the concept, but call this out if asked in an interview.

## Possible extensions

- Swap Chroma for a persistent store (Pinecone/Weaviate) for multi-session use
- Add RAGAS or DeepEval for more rigorous automated evaluation
- Add streaming responses in the chat tab for better perceived latency
- Support multi-document comparison ("compare these two papers")