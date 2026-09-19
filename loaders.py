"""
loaders.py
----------
Source loading utilities for:
- YouTube videos
- PDF files
- arXiv papers
- Web articles
"""

import io
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi


# ---------------------------------------------------------------------------
# YouTube helpers
# ---------------------------------------------------------------------------

def extract_youtube_id(url: str) -> str:
    """
    Extract a YouTube video ID from common YouTube URL formats.
    """

    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?&]+)",
        r"youtube\.com/embed/([^?&]+)",
        r"youtube\.com/shorts/([^?&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    raise ValueError("Could not extract YouTube video ID.")


def _fetch_transcript_raw(video_id: str):
    """
    Supports different versions of youtube-transcript-api.
    """

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        return YouTubeTranscriptApi.get_transcript(video_id)

    api = YouTubeTranscriptApi()

    fetched = api.fetch(video_id)

    return [
        {
            "start": snippet.start,
            "duration": snippet.duration,
            "text": snippet.text,
        }
        for snippet in fetched
    ]


def load_youtube(url: str) -> dict:
    """
    Load a YouTube transcript.
    """

    video_id = extract_youtube_id(url)

    transcript = _fetch_transcript_raw(video_id)

    text_parts = []

    for item in transcript:

        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", "")

        if text:
            text_parts.append(text)

    if not text_parts:
        raise ValueError(
            "No transcript text was found for this YouTube video."
        )

    full_text = " ".join(text_parts)

    return {
        "source_type": "youtube",
        "title": f"YouTube video ({video_id})",
        "text": full_text,
        "metadata": {
            "video_id": video_id,
            "url": url,
        },
    }


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def load_pdf(file) -> dict:
    """
    Load a PDF from:
    - Streamlit UploadedFile
    - file path
    - bytes
    """

    # Streamlit UploadedFile
    if hasattr(file, "getvalue"):

        pdf_bytes = file.getvalue()

        filename = getattr(
            file,
            "name",
            "Uploaded PDF",
        )

        reader = PdfReader(
            io.BytesIO(pdf_bytes)
        )

    # File path
    elif isinstance(file, (str, Path)):

        path = Path(file)

        filename = path.name

        reader = PdfReader(str(path))

    # Raw bytes
    elif isinstance(file, bytes):

        filename = "Uploaded PDF"

        reader = PdfReader(
            io.BytesIO(file)
        )

    else:

        raise TypeError(
            "Unsupported PDF input type."
        )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        text = page.extract_text() or ""

        if text.strip():

            pages.append(
                f"[Page {page_number}]\n{text}"
            )

    if not pages:

        raise ValueError(
            "No readable text was found in this PDF. "
            "If it is a scanned/image-only PDF, OCR may be required."
        )

    full_text = "\n\n".join(pages)

    return {
        "source_type": "pdf",
        "title": filename,
        "text": full_text,
        "metadata": {
            "filename": filename,
            "page_count": len(reader.pages),
        },
    }


# ---------------------------------------------------------------------------
# Web article helpers
# ---------------------------------------------------------------------------

def load_web_article(url: str) -> dict:
    """
    Load readable text from a web page.
    """

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/131.0 Safari/537.36"
            )
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n",
        strip=True,
    )

    if not text:
        raise ValueError(
            "No readable text was found on this webpage."
        )

    title = (
        soup.title.get_text(strip=True)
        if soup.title
        else url
    )

    return {
        "source_type": "web",
        "title": title,
        "text": text,
        "metadata": {
            "url": url,
        },
    }


# ---------------------------------------------------------------------------
# arXiv helpers
# ---------------------------------------------------------------------------

def load_arxiv(url: str) -> dict:
    """
    Convert an arXiv abstract URL into its PDF URL
    and process the PDF.
    """

    match = re.search(
        r"arxiv\.org/(?:abs|pdf)/([^/?#]+)",
        url,
    )

    if not match:
        raise ValueError(
            "Could not determine the arXiv paper ID."
        )

    paper_id = match.group(1)

    pdf_url = (
        f"https://arxiv.org/pdf/{paper_id}"
    )

    response = requests.get(
        pdf_url,
        timeout=30,
        headers={
            "User-Agent": "InsightExtractor/1.0"
        },
    )

    response.raise_for_status()

    result = load_pdf(
        response.content
    )

    result["source_type"] = "pdf"

    result["metadata"]["url"] = url
    result["metadata"]["arxiv_id"] = paper_id

    result["title"] = (
        f"arXiv paper ({paper_id})"
    )

    return result


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def detect_source_type(url: str) -> str:
    """
    Detect the source type from a URL.
    """

    url_lower = url.lower()

    if (
        "youtube.com" in url_lower
        or "youtu.be" in url_lower
    ):
        return "YouTube"

    if "arxiv.org" in url_lower:
        return "arXiv"

    if url_lower.endswith(".pdf"):
        return "PDF"

    return "Web article"


# ---------------------------------------------------------------------------
# Main URL loader
# ---------------------------------------------------------------------------

def load_source(url: str) -> dict:
    """
    Load a source from a URL.
    """

    source_type = detect_source_type(url)

    if source_type == "YouTube":

        return load_youtube(url)

    if source_type == "arXiv":

        return load_arxiv(url)

    if source_type == "PDF":

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "InsightExtractor/1.0"
            },
        )

        response.raise_for_status()

        result = load_pdf(
            response.content
        )

        result["metadata"]["url"] = url

        return result

    return load_web_article(url)