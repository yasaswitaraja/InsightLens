import os
import re
import tempfile

import requests
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from youtube_transcript_api import YouTubeTranscriptApi
from types import SimpleNamespace

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
    """Get public YouTube metadata without making analysis depend on it.

    First use YouTube's oEmbed endpoint. If it is unavailable, try yt-dlp.
    If both methods fail, return a safe fallback so transcript analysis can
    still continue.
    """
    watch_url = youtube_watch_url(video_id)
    metadata = {
        "title": None,
        "channel": None,
        "thumbnail_url": None,
    }

    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": watch_url, "format": "json"},
            timeout=6,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        data = response.json()
        metadata.update({
            "title": data.get("title"),
            "channel": data.get("author_name"),
            "thumbnail_url": data.get("thumbnail_url"),
        })
    except (requests.RequestException, ValueError, TypeError):
        # Metadata is helpful for the UI, but must not block transcript work.
        pass

    if not metadata["title"]:
        try:
            import yt_dlp

            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 8,
                "retries": 1,
                "extractor_retries": 1,
            }
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(watch_url, download=False)

            if info:
                metadata["title"] = info.get("title")
                metadata["channel"] = (
                    info.get("channel")
                    or info.get("uploader")
                    or metadata["channel"]
                )
                metadata["thumbnail_url"] = (
                    info.get("thumbnail") or metadata["thumbnail_url"]
                )
        except Exception:
            # Some videos restrict metadata access; keep the app usable.
            pass

    metadata["title"] = (
        str(metadata["title"]).strip()
        if metadata.get("title")
        else f"YouTube video {video_id}"
    )
    if metadata.get("channel"):
        metadata["channel"] = str(metadata["channel"]).strip()

    return metadata


def get_free_api_transcript(url: str):
    """Retrieve timestamped captions from FreeTranscriptAPI."""
    response = requests.get(
        "https://api.freetranscriptapi.com/v1/transcript",
        params={"video_url": url},
        timeout=45,
    )
    response.raise_for_status()

    data = response.json()
    segments = data.get("transcript")

    if not isinstance(segments, list) or not segments:
        raise RuntimeError(
            "FreeTranscriptAPI returned no transcript segments."
        )

    transcript_items = []

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        text = str(segment.get("text", "")).strip()
        if not text:
            continue

        transcript_items.append(
            SimpleNamespace(
                text=text,
                start=float(segment.get("start", 0)),
                duration=float(segment.get("duration", 0)),
            )
        )

    if not transcript_items:
        raise RuntimeError("The returned transcript was empty.")

    return transcript_items



def get_youtube_transcript(url: str):
    video_id = extract_video_id(url)

    if not video_id:
        raise RuntimeError("Invalid YouTube URL.")

    video_metadata = get_youtube_metadata(video_id)
    video_title = video_metadata["title"]
    transcript = None
    last_error = None

    # First attempt: free managed transcript API.
    try:
        transcript = get_free_api_transcript(url)
    except Exception as exc:
        last_error = exc

    # Fallback: existing YouTube transcript library.
    if transcript is None:
        api = YouTubeTranscriptApi()

        for languages in [["en"], ["en", "hi", "te"], None]:
            try:
                if languages:
                    transcript = api.fetch(
                        video_id,
                        languages=languages,
                    )
                else:
                    transcript = None
                    for item in api.list(video_id):
                        transcript = item.fetch()
                        break

                    if transcript is None:
                        raise RuntimeError(
                            "No transcript tracks were found."
                        )

                break

            except Exception as exc:
                last_error = exc
                transcript = None

    if transcript is None:
        raise RuntimeError(
            "YouTube transcript retrieval failed. "
            f"Last error: {last_error}"
        )

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
                    "source": video_title,
                    "source_type": "youtube",
                    "video_id": video_id,
                    "title": video_title,
                    "channel": video_metadata.get("channel"),
                    "thumbnail_url": video_metadata.get("thumbnail_url"),
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

    raise RuntimeError("The transcript was empty.")


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

def load_transcript_documents(content: bytes, filename: str):
    """Convert an uploaded TXT or SRT transcript into RAG documents."""
    if not content:
        raise RuntimeError("The transcript file is empty.")

    try:
        transcript_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "The transcript must be a UTF-8 encoded TXT or SRT file."
        ) from exc

    if filename.lower().endswith(".srt"):
        transcript_text = re.sub(
            r"^\s*\d+\s*$",
            "",
            transcript_text,
            flags=re.MULTILINE,
        )
        transcript_text = re.sub(
            r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*"
            r"\d{2}:\d{2}:\d{2}[,.]\d{3}",
            "",
            transcript_text,
        )

    transcript_text = re.sub(
        r"<[^>]+>",
        " ",
        transcript_text,
    )
    transcript_text = re.sub(
        r"\s+",
        " ",
        transcript_text,
    ).strip()

    if not transcript_text:
        raise RuntimeError(
            "No readable transcript text was found in the file."
        )

    max_group_chars = 2500
    documents = []

    for start_index in range(0, len(transcript_text), max_group_chars):
        segment_text = transcript_text[start_index:start_index + max_group_chars]

        documents.append(
            Document(
                page_content=segment_text,
                metadata={
                    "source": filename,
                    "source_type": "youtube_transcript_upload",
                    "filename": filename,
                    "segment": len(documents) + 1,
                },
            )
        )

    return documents