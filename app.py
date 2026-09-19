import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pipeline import (
    process_source,
    answer_question
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="InsightLens",
    page_icon="🔎",
    layout="wide"
)


# ============================================================
# LOAD LOCAL .ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# LOAD API KEYS
# ============================================================

# First try the local .env / environment variables.
groq_key = os.getenv("GROQ_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")


# ------------------------------------------------------------
# Streamlit Cloud fallback
# ------------------------------------------------------------
# This block is only reached if the environment variable
# wasn't found.
#
# Therefore, when running locally with .env, Streamlit will
# NOT try to access st.secrets and will NOT show the
# "No secrets found" warning.
# ------------------------------------------------------------

if not groq_key:

    try:
        groq_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        groq_key = None


if not gemini_key:

    try:
        gemini_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        gemini_key = None


# ============================================================
# MAKE KEYS AVAILABLE TO LANGCHAIN
# ============================================================

if groq_key:
    os.environ["GROQ_API_KEY"] = groq_key

if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key


# ============================================================
# CHECK API CONFIGURATION
# ============================================================

if not groq_key:

    st.error(
        "Groq API key is not configured."
    )

    st.stop()


if not gemini_key:

    st.error(
        "Gemini API key is not configured."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title("🔎 InsightLens")

st.markdown(
    """
    ### Multi-Source Insight & Q&A Generator

    Analyze **YouTube videos, research papers, web articles, and PDF documents**
    using AI-powered summarization and retrieval-augmented question answering.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("📚 Source")

    source_type = st.radio(
        "Choose source type",
        [
            "🌐 URL",
            "📄 Local PDF"
        ]
    )

    st.divider()

    st.caption(
        "LLM: Groq • Embeddings: Gemini • Vector DB: Chroma"
    )


# ============================================================
# SOURCE INPUT
# ============================================================

source = None
uploaded_file = None


if source_type == "🌐 URL":

    source = st.text_input(
        "Enter a YouTube, research paper, or web article URL",
        placeholder="https://..."
    )

else:

    uploaded_file = st.file_uploader(
        "Choose a PDF from your computer",
        type=["pdf"]
    )


# ============================================================
# ANALYZE SOURCE
# ============================================================

analyze_button = st.button(
    "🚀 Analyze Source",
    type="primary",
    use_container_width=True
)


if analyze_button:

    # ========================================================
    # URL
    # ========================================================

    if source_type == "🌐 URL":

        if not source:

            st.warning(
                "Please enter a URL."
            )

            st.stop()

        try:

            with st.spinner(
                "Loading and analyzing source..."
            ):

                result = process_source(
                    source=source,
                    source_type="url"
                )

            # Store result for later questions
            st.session_state["result"] = result

            st.success(
                "Source analyzed successfully!"
            )

        except Exception as e:

            st.error(
                f"Error while processing source: {e}"
            )


    # ========================================================
    # LOCAL PDF
    # ========================================================

    elif source_type == "📄 Local PDF":

        if uploaded_file is None:

            st.warning(
                "Please upload a PDF."
            )

            st.stop()

        try:

            with st.spinner(
                "Reading and analyzing PDF..."
            ):

                result = process_source(
                    source=uploaded_file,
                    source_type="pdf"
                )

            # Store result for later questions
            st.session_state["result"] = result

            st.success(
                "PDF analyzed successfully!"
            )

        except Exception as e:

            st.error(
                f"Error while processing PDF: {e}"
            )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "result" in st.session_state:

    result = st.session_state["result"]

    st.divider()

    st.header("📌 Insights")


    # ========================================================
    # SUMMARY
    # ========================================================

    if isinstance(result, dict):

        if "summary" in result:

            st.subheader("📝 Summary")

            st.write(
                result["summary"]
            )


        # ====================================================
        # KEY POINTS
        # ====================================================

        if "key_points" in result:

            st.subheader("🔑 Key Points")

            key_points = result["key_points"]

            if isinstance(key_points, list):

                for point in key_points:

                    st.markdown(
                        f"- {point}"
                    )

            else:

                st.write(
                    key_points
                )


        # ====================================================
        # CHUNK INFORMATION
        # ====================================================

        if "chunks" in result:

            try:

                chunk_count = len(
                    result["chunks"]
                )

                st.caption(
                    f"Processed {chunk_count} document chunks."
                )

            except Exception:

                pass


    # ========================================================
    # QUESTION ANSWERING
    # ========================================================

    st.divider()

    st.header("💬 Ask Questions")

    question = st.text_input(
        "Ask something about this source",
        placeholder="What are the main findings?"
    )


    ask_button = st.button(
        "🔍 Ask",
        use_container_width=True
    )


    if ask_button:

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            try:

                with st.spinner(
                    "Searching the source..."
                ):

                    answer = answer_question(
                        question=question,
                        vector_store=result["vector_store"]
                    )

                st.subheader(
                    "Answer"
                )

                st.write(
                    answer
                )

            except Exception as e:

                st.error(
                    f"Unable to answer the question: {e}"
                )