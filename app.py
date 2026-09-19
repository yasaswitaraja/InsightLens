import os
import streamlit as st
from dotenv import load_dotenv

from pipeline import (
    process_source,
    answer_question,
    generate_summary
)


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="InsightLens",
    page_icon="🔎",
    layout="wide"
)

load_dotenv()


# ============================================================
# LOAD API KEYS
# ============================================================

def get_secret(name):
    """
    Get API key from Streamlit Cloud Secrets first.
    Fall back to local .env when running locally.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass

    return os.getenv(name)


groq_key = get_secret("GROQ_API_KEY")
gemini_key = get_secret("GEMINI_API_KEY")


# Make keys available to LangChain libraries
if groq_key:
    os.environ["GROQ_API_KEY"] = groq_key

if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key


# ============================================================
# CHECK API KEYS
# ============================================================

if not groq_key or not gemini_key:
    st.error(
        "Application configuration is incomplete. "
        "Please configure the required API keys."
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
# PROCESS BUTTON
# ============================================================

process_button = st.button(
    "🚀 Analyze Source",
    type="primary",
    use_container_width=True
)


# ============================================================
# PROCESS SOURCE
# ============================================================

if process_button:

    if source_type == "🌐 URL":

        if not source:
            st.warning("Please enter a URL.")
            st.stop()

        try:

            with st.spinner("Loading and analyzing source..."):

                result = process_source(
                    source=source,
                    source_type="url"
                )

            st.session_state["result"] = result

            st.success("Source analyzed successfully!")

        except Exception as e:

            st.error(f"Error while processing source: {e}")

    else:

        if uploaded_file is None:
            st.warning("Please upload a PDF.")
            st.stop()

        try:

            with st.spinner("Reading and analyzing PDF..."):

                result = process_source(
                    source=uploaded_file,
                    source_type="pdf"
                )

            st.session_state["result"] = result

            st.success("PDF analyzed successfully!")

        except Exception as e:

            st.error(f"Error while processing PDF: {e}")


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "result" in st.session_state:

    result = st.session_state["result"]

    st.divider()

    st.header("📌 Insights")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if isinstance(result, dict):

        if "summary" in result:

            st.subheader("📝 Summary")

            st.write(result["summary"])

        # ----------------------------------------------------
        # KEY POINTS
        # ----------------------------------------------------

        if "key_points" in result:

            st.subheader("🔑 Key Points")

            key_points = result["key_points"]

            if isinstance(key_points, list):

                for point in key_points:
                    st.markdown(f"- {point}")

            else:

                st.write(key_points)

        # ----------------------------------------------------
        # CHUNKS / DOCUMENT INFO
        # ----------------------------------------------------

        if "chunks" in result:

            st.caption(
                f"Processed {len(result['chunks'])} document chunks."
            )


    # ========================================================
    # QUESTION ANSWERING
    # ========================================================

    st.divider()

    st.header("💬 Ask Questions")

    question = st.text_input(
        "Ask something about this source",
        placeholder="What are the main findings?"
    )

    if st.button(
        "🔍 Ask",
        use_container_width=True
    ):

        if not question:

            st.warning("Please enter a question.")

        else:

            try:

                with st.spinner("Searching the source..."):

                    answer = answer_question(
                        question=question,
                        result=result
                    )

                st.subheader("Answer")

                st.write(answer)

            except Exception as e:

                st.error(
                    f"Unable to answer the question: {e}"
                )