import os
import re
import tempfile

import requests
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str):
    if not url:
        return None

    patterns = [
        r"(?:youtube\.com/watch\?.*?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def format_timestamp(seconds: float):
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

    return f"{minutes:02d}:{remaining_seconds:02d}"


def youtube_watch_url(video_id: str):
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_timestamp_url(video_id: str, seconds: float = 0):
    return f"{youtube_watch_url(video_id)}&t={int(seconds)}s"


def get_youtube_metadata(video_id: str):
    response = requests.get(
        "https://www.youtube.com/oembed",
        params={
            "url": youtube_watch_url(video_id),
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "title": data.get("title"),
        "channel": data.get("author_name"),
        "thumbnail_url": data.get("thumbnail_url"),
    }


def get_youtube_transcript(url: str):
    video_id = extract_video_id(url)

    if not video_id:
        raise RuntimeError("Invalid YouTube URL.")

    api = YouTubeTranscriptApi()
    last_error = None

    language_attempts = [
        ["en"],
        ["en", "hi", "te"],
        None,
    ]

    for languages in language_attempts:
        try:
            if languages:
                transcript = api.fetch(
                    video_id,
                    languages=languages,
                )
            else:
                transcript_list = api.list(video_id)
                transcript = None

                for transcript_item in transcript_list:
                    transcript = transcript_item.fetch()
                    break

                if transcript is None:
                    raise RuntimeError("No transcript tracks were found.")

            documents = []
            caption_group = []
            group_start = None
            group_end = 0.0
            group_chars = 0
            max_group_chars = 2500

            def save_group():
                if not caption_group:
                    return

                documents.append(
                    Document(
                        page_content=" ".join(caption_group),
                        metadata={
                            "source": f"YouTube video {video_id}",
                            "source_type": "youtube",
                            "video_id": video_id,
                            "segment": len(documents) + 1,
                            "start": group_start,
                            "duration": max(0.0, group_end - group_start),
                            "timestamp": format_timestamp(group_start),
                            "timestamp_url": youtube_timestamp_url(
                                video_id, group_start
                            ),
                        },
                    )
                )

            for item in transcript:
                caption_text = str(
                    getattr(item, "text", "")
                ).strip()

                if not caption_text:
                    continue

                start = float(getattr(item, "start", 0))
                duration = float(getattr(item, "duration", 0))

                if (
                    caption_group
                    and group_chars + len(caption_text) + 1
                    > max_group_chars
                ):
                    save_group()
                    caption_group = []
                    group_start = None
                    group_chars = 0

                if group_start is None:
                    group_start = start

                caption_group.append(caption_text)
                group_chars += len(caption_text) + 1
                group_end = start + duration

            save_group()

            if documents:
                return documents, "available"

            last_error = RuntimeError("The transcript was empty.")

        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "YouTube transcript could not be retrieved. "
        f"Reason: {last_error}"
    )


def load_pdf_documents(content: bytes, filename: str):
    if not content:
        raise RuntimeError("The uploaded PDF is empty.")

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = temporary_file.name

        documents = PyPDFLoader(temporary_path).load()

        for document in documents:
            document.metadata["source_type"] = "pdf"
            document.metadata["source"] = filename
            document.metadata["filename"] = filename

        if not documents or not any(
            document.page_content.strip() for document in documents
        ):
            raise RuntimeError(
                "No readable text was found in the PDF. "
                "If it contains scanned pages, OCR may be required."
            )

        return documents

    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def load_pdf(file_path: str):
    with open(file_path, "rb") as pdf_file:
        content = pdf_file.read()

    return load_pdf_documents(
        content,
        os.path.basename(file_path),
    )


def load_url_documents(url: str):
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130 Safari/537.36"
            )
        },
    )
    response.raise_for_status()

    html = response.text

    html = re.sub(
        r"<(script|style|noscript)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise RuntimeError(
            "No readable text was found on this webpage."
        )

    return [
        Document(
            page_content=text,
            metadata={
                "source": url,
                "source_type": "web",
                "url": url,
            },
        )
    ]


def load_webpage(url: str):
    return load_url_documents(url)
