"""
app.py
------
Streamlit front-end for the Multi-Source Insight & Q&A Generator.

Run with:
    streamlit run app.py
"""

import os
from dotenv import load_dotenv
import streamlit as st

from loaders import (
    load_source,
    load_pdf,
    detect_source_type,
)

from pipeline import (
    chunk_text,
    build_vectorstore,
    summarize,
    generate_qa,
    answer_question,
)

from qa_eval import (
    evaluate_groundedness,
    EvalReport,
)


load_dotenv()


st.set_page_config(
    page_title="Insight & Q&A Extractor",
    page_icon="🔎",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

for key in [
    "vectorstore",
    "docs",
    "raw",
    "summary",
    "qa_set",
    "chat_history",
    "eval_report",
]:

    if key not in st.session_state:
        st.session_state[key] = None


if st.session_state.chat_history is None:
    st.session_state.chat_history = []


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("🔎 Insight Extractor")

st.sidebar.caption(
    "YouTube • Research Papers • Web Articles • Local PDFs"
)


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------

groq_key = os.getenv(
    "GROQ_API_KEY",
    "",
)

gemini_key = os.getenv(
    "GEMINI_API_KEY",
    "",
)


if groq_key:

    st.sidebar.success(
        "✅ Groq LLM key loaded from .env"
    )

else:

    groq_key = st.sidebar.text_input(
        "Groq API Key",
        type="password",
        help="Add GROQ_API_KEY to your .env file.",
    )

    if groq_key:

        os.environ["GROQ_API_KEY"] = groq_key


if gemini_key:

    st.sidebar.success(
        "✅ Gemini embedding key loaded from .env"
    )

else:

    gemini_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        help="Gemini is used for embeddings.",
    )

    if gemini_key:

        os.environ["GEMINI_API_KEY"] = gemini_key


# ---------------------------------------------------------------------------
# Source selection
# ---------------------------------------------------------------------------

st.sidebar.markdown("---")

source_mode = st.sidebar.radio(
    "Choose source type",
    [
        "🌐 URL",
        "📄 Local PDF",
    ],
)


url = None
uploaded_pdf = None


if source_mode == "🌐 URL":

    url = st.sidebar.text_input(
        "Paste a URL",
        placeholder=(
            "YouTube / PDF / arXiv / article URL"
        ),
    )


else:

    uploaded_pdf = st.sidebar.file_uploader(
        "Choose a PDF from your computer",
        type=["pdf"],
        help=(
            "Select a PDF from Downloads, Documents, "
            "Desktop, or any other folder on your computer."
        ),
    )

    if uploaded_pdf:

        st.sidebar.success(
            f"📄 {uploaded_pdf.name}"
        )


# ---------------------------------------------------------------------------
# Process button
# ---------------------------------------------------------------------------

process_btn = st.sidebar.button(
    "Process source",
    type="primary",
    use_container_width=True,
)


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

st.sidebar.markdown("---")

if source_mode == "🌐 URL":

    st.sidebar.markdown(
        "**Examples to try:**\n"
        "- A YouTube tutorial or talk\n"
        "- An arXiv paper\n"
        "- Any blog post or news article URL"
    )

else:

    st.sidebar.markdown(
        "**Local PDF examples:**\n"
        "- Resume\n"
        "- College notes\n"
        "- Research paper\n"
        "- Project documentation\n"
        "- Personal study material"
    )


st.sidebar.markdown("---")

st.sidebar.caption(
    "LLM: Groq • Embeddings: Gemini • Vector DB: Chroma"
)


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

if process_btn:

    # ---------------------------------------------------------------
    # Check API keys
    # ---------------------------------------------------------------

    if not groq_key:

        st.error(
            "Please provide a Groq API key."
        )

    elif not gemini_key:

        st.error(
            "Please provide a Gemini API key "
            "for embeddings."
        )

    # ---------------------------------------------------------------
    # URL validation
    # ---------------------------------------------------------------

    elif (
        source_mode == "🌐 URL"
        and not url
    ):

        st.error(
            "Please paste a URL."
        )

    # ---------------------------------------------------------------
    # PDF validation
    # ---------------------------------------------------------------

    elif (
        source_mode == "📄 Local PDF"
        and not uploaded_pdf
    ):

        st.error(
            "Please choose a PDF file."
        )

    else:

        try:

            # -----------------------------------------------------------
            # Extract source
            # -----------------------------------------------------------

            if source_mode == "🌐 URL":

                detected_type = detect_source_type(
                    url
                )

                with st.spinner(
                    f"Detected source type: "
                    f"{detected_type} "
                    "— extracting content..."
                ):

                    raw = load_source(
                        url
                    )

            else:

                with st.spinner(
                    "Reading PDF from your computer..."
                ):

                    raw = load_pdf(
                        uploaded_pdf
                    )

            st.session_state.raw = raw


            # -----------------------------------------------------------
            # Chunk + embed
            # -----------------------------------------------------------

            with st.spinner(
                "Chunking and creating Gemini embeddings..."
            ):

                docs = chunk_text(
                    raw
                )

                st.session_state.docs = docs

                vectorstore = build_vectorstore(
                    docs
                )

                st.session_state.vectorstore = (
                    vectorstore
                )


            # -----------------------------------------------------------
            # Generate summary
            # -----------------------------------------------------------

            with st.spinner(
                "Generating structured summary with Groq..."
            ):

                summary = summarize(
                    docs
                )

                st.session_state.summary = (
                    summary
                )


            # -----------------------------------------------------------
            # Generate grounded Q&A
            # -----------------------------------------------------------

            with st.spinner(
                "Generating grounded Q&A with Groq..."
            ):

                qa_set = generate_qa(
                    vectorstore,
                    raw["title"],
                )

                st.session_state.qa_set = (
                    qa_set
                )


            # -----------------------------------------------------------
            # Reset chat/evaluation
            # -----------------------------------------------------------

            st.session_state.chat_history = []

            st.session_state.eval_report = None


            # -----------------------------------------------------------
            # Success
            # -----------------------------------------------------------

            st.success(
                f"Processed: "
                f"{raw['title']} "
                f"({len(docs)} chunks)"
            )


        except Exception as e:

            st.error(
                f"Failed to process source: {e}"
            )


# ---------------------------------------------------------------------------
# Main area — before processing
# ---------------------------------------------------------------------------

if st.session_state.summary is None:

    st.title(
        "Multi-Source Insight & Q&A Generator"
    )

    st.write(
        "Use a **YouTube link**, **research paper**, "
        "**web article**, or a **PDF from your computer** "
        "to generate a structured summary and grounded Q&A."
    )

    st.info(
        "Under the hood: source-specific chunking → "
        "Gemini embeddings → Chroma vector store → "
        "Groq-powered summarization → "
        "retrieval-grounded Q&A generation → "
        "Groq LLM-as-judge evaluation."
    )


# ---------------------------------------------------------------------------
# Main area — after processing
# ---------------------------------------------------------------------------

else:

    summary = st.session_state.summary

    raw = st.session_state.raw


    st.title(
        summary.title
    )


    source_url = raw["metadata"].get(
        "url",
        "",
    )


    if source_url:

        st.caption(
            f"Source: "
            f"{raw['source_type'].upper()} — "
            f"{source_url}"
        )

    else:

        st.caption(
            f"Source: "
            f"{raw['source_type'].upper()} — "
            f"{raw['metadata'].get('filename', raw['title'])}"
        )


    tab_summary, tab_qa, tab_chat, tab_eval = st.tabs(
        [
            "📋 Summary",
            "❓ Auto Q&A",
            "💬 Ask a question",
            "🧪 Eval",
        ]
    )


    # -----------------------------------------------------------------------
    # Summary tab
    # -----------------------------------------------------------------------

    with tab_summary:

        st.subheader(
            "One-line summary"
        )

        st.write(
            summary.one_line_summary
        )


        st.subheader(
            "Key points"
        )

        for p in summary.key_points:

            st.markdown(
                f"- {p}"
            )


        st.subheader(
            "Key claims & evidence"
        )

        for c in summary.key_claims:

            with st.expander(
                c.claim
            ):

                st.write(
                    c.supporting_evidence
                )


        if summary.limitations:

            st.subheader(
                "Limitations / open questions"
            )

            for l in summary.limitations:

                st.markdown(
                    f"- {l}"
                )


        st.subheader(
            "Best suited for"
        )

        st.write(
            summary.audience
        )


    # -----------------------------------------------------------------------
    # Auto Q&A tab
    # -----------------------------------------------------------------------

    with tab_qa:

        qa_set = st.session_state.qa_set

        for i, pair in enumerate(
            qa_set.qa_pairs,
            1,
        ):

            grounded_badge = (
                "🟢 grounded"
                if pair.grounded
                else "🟡 uncertain"
            )


            st.markdown(
                f"**Q{i}: {pair.question}**  \n"
                f"{grounded_badge}"
            )


            st.write(
                pair.answer
            )


            st.markdown(
                "---"
            )


    # -----------------------------------------------------------------------
    # Interactive chat tab
    # -----------------------------------------------------------------------

    with tab_chat:

        question = st.text_input(
            "Ask a follow-up question about this source"
        )


        if st.button(
            "Ask"
        ) and question:

            with st.spinner(
                "Retrieving relevant chunks and "
                "answering with Groq..."
            ):

                result = answer_question(
                    st.session_state.vectorstore,
                    question,
                )


                st.session_state.chat_history.append(
                    (
                        question,
                        result,
                    )
                )


        for q, result in reversed(
            st.session_state.chat_history
        ):

            st.markdown(
                f"**Q: {q}**"
            )


            st.write(
                result["answer"]
            )


            with st.expander(
                "Sources used"
            ):

                for src in result["sources"]:

                    st.markdown(
                        f"**[{src['block']}]** "
                        f"({src['location']})"
                    )


                    st.caption(
                        src["excerpt"]
                        + "..."
                    )


            st.markdown(
                "---"
            )


    # -----------------------------------------------------------------------
    # Evaluation tab
    # -----------------------------------------------------------------------

    with tab_eval:

        st.write(
            "Runs a Groq LLM-as-judge check on the "
            "auto-generated Q&A pairs to verify that "
            "each answer is supported by the source."
        )


        if st.button(
            "Run groundedness eval"
        ):

            with st.spinner(
                "Judging each Q&A pair against "
                "the source with Groq..."
            ):

                sample_text = "\n\n".join(
                    d.page_content
                    for d in st.session_state.docs[:15]
                )


                report: EvalReport = (
                    evaluate_groundedness(
                        st.session_state.qa_set.qa_pairs,
                        sample_text,
                    )
                )


                st.session_state.eval_report = (
                    report
                )


        if st.session_state.eval_report:

            report = (
                st.session_state.eval_report
            )


            st.metric(
                "Pass rate",
                f"{report.pass_rate * 100:.0f}%",
                help=(
                    f"{report.grounded_count}/"
                    f"{report.total_count} answers "
                    "fully grounded"
                ),
            )


            for v in report.verdicts:

                marker = (
                    "✅"
                    if v.verdict == "grounded"
                    else (
                        "⚠️"
                        if v.verdict
                        == "partially_grounded"
                        else "❌"
                    )
                )


                st.markdown(
                    f"{marker} **{v.verdict}** — "
                    f"{v.question}"
                )


                st.caption(
                    v.reasoning
                )