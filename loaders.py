# loaders.py

import os
import tempfile

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    WebBaseLoader,
)

from youtube_transcript_api import YouTubeTranscriptApi


# ============================================================
# YOUTUBE
# ============================================================

def load_youtube(url):
    """
    Load transcript from a YouTube video.
    """

    try:
        # Extract video ID
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]

        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]

        elif "youtube.com/shorts/" in url:
            video_id = url.split("youtube.com/shorts/")[1].split("?")[0]

        else:
            raise ValueError("Invalid YouTube URL.")

        # Get transcript
        api = YouTubeTranscriptApi()

        transcript = api.fetch(video_id)

        text = " ".join(
            item.text
            for item in transcript
        )

        if not text.strip():
            raise ValueError(
                "No transcript was found for this video."
            )

        return [
            Document(
                page_content=text,
                metadata={
                    "source": url,
                    "source_type": "youtube",
                    "video_id": video_id,
                },
            )
        ]

    except Exception as e:

        raise RuntimeError(
            f"Could not load YouTube transcript: {e}"
        )


# ============================================================
# WEB ARTICLE
# ============================================================

def load_web_article(url):
    """
    Load text from a normal web page/article.
    """

    try:

        loader = WebBaseLoader(url)

        documents = loader.load()

        if not documents:
            raise ValueError(
                "No content could be extracted from the webpage."
            )

        for document in documents:

            document.metadata["source"] = url
            document.metadata["source_type"] = "web"

        return documents

    except Exception as e:

        raise RuntimeError(
            f"Could not load webpage: {e}"
        )


# ============================================================
# ARXIV / RESEARCH PAPER
# ============================================================

def load_arxiv(url):
    """
    Load an arXiv research paper.

    arXiv PDF URLs are handled as PDFs.
    """

    try:

        # arXiv pages often look like:
        # https://arxiv.org/abs/xxxx.xxxxx
        #
        # Convert them to PDF URL.

        if "/abs/" in url:

            paper_id = url.split("/abs/")[1].split("?")[0]

            pdf_url = (
                f"https://arxiv.org/pdf/{paper_id}.pdf"
            )

        elif "/pdf/" in url:

            pdf_url = url

        else:

            pdf_url = url

        import requests

        response = requests.get(
            pdf_url,
            timeout=30
        )

        response.raise_for_status()

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(response.content)

            temp_path = temp_file.name

        try:

            loader = PyPDFLoader(temp_path)

            documents = loader.load()

            for document in documents:

                document.metadata["source"] = url
                document.metadata["source_type"] = "research_paper"

            return documents

        finally:

            if os.path.exists(temp_path):

                os.remove(temp_path)

    except Exception as e:

        raise RuntimeError(
            f"Could not load research paper: {e}"
        )


# ============================================================
# LOCAL PDF
# ============================================================

def load_pdf(uploaded_file):
    """
    Load a PDF uploaded through Streamlit.
    """

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(
                uploaded_file.getbuffer()
            )

            temp_path = temp_file.name

        try:

            loader = PyPDFLoader(temp_path)

            documents = loader.load()

            for document in documents:

                document.metadata["source"] = (
                    uploaded_file.name
                )

                document.metadata["source_type"] = (
                    "local_pdf"
                )

            return documents

        finally:

            if os.path.exists(temp_path):

                os.remove(temp_path)

    except Exception as e:

        raise RuntimeError(
            f"Could not read PDF: {e}"
        )


# ============================================================
# DETECT URL TYPE
# ============================================================

def detect_source_type(url):
    """
    Automatically determine what type of URL was provided.
    """

    url_lower = url.lower()

    # YouTube
    if (
        "youtube.com" in url_lower
        or "youtu.be" in url_lower
    ):

        return "youtube"

    # arXiv
    if "arxiv.org" in url_lower:

        return "research_paper"

    # Otherwise treat it as a web article
    return "web"


# ============================================================
# MAIN LOADER
# ============================================================

def load_source(source, source_type):
    """
    Main entry point used by app.py / pipeline.py.
    """

    # --------------------------------------------------------
    # LOCAL PDF
    # --------------------------------------------------------

    if source_type == "pdf":

        return load_pdf(source)

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if source_type == "url":

        detected_type = detect_source_type(source)

        if detected_type == "youtube":

            return load_youtube(source)

        elif detected_type == "research_paper":

            return load_arxiv(source)

        elif detected_type == "web":

            return load_web_article(source)

        else:

            raise ValueError(
                "Unsupported URL type."
            )

    raise ValueError(
        f"Unsupported source type: {source_type}"
    )