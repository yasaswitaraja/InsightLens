"""
pipeline.py
-----------
The RAG + insight-generation engine.

Responsibilities:
1. Chunk source text (different strategy per source type)
2. Embed chunks into a Chroma vector store using Gemini embeddings
3. Generate a structured summary using Groq
4. Auto-generate likely Q&A pairs using Groq
5. Answer arbitrary follow-up questions using Groq with citations

Architecture:
    Source
       ↓
    Chunking
       ↓
    Gemini Embeddings
       ↓
    Chroma
       ↓
    Groq LLM
       ↓
    Summary / Q&A / Chat
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import (
    PydanticOutputParser,
    StrOutputParser,
)


# ---------------------------------------------------------------------------
# Structured output schemas
# ---------------------------------------------------------------------------

class KeyClaim(BaseModel):
    claim: str = Field(
        description="A single key claim or finding"
    )

    supporting_evidence: str = Field(
        description="Brief evidence or reasoning from the source"
    )


class StructuredSummary(BaseModel):
    title: str

    one_line_summary: str = Field(
        description="A single sentence capturing the core idea"
    )

    key_points: List[str] = Field(
        description="3-6 main points, each one sentence"
    )

    key_claims: List[KeyClaim] = Field(
        description="Notable claims with their supporting evidence"
    )

    limitations: List[str] = Field(
        default_factory=list,
        description="Caveats, limitations, or open questions mentioned "
                    "or implied by the source"
    )

    audience: str = Field(
        description="Who this content is most useful for"
    )


class QAPair(BaseModel):
    question: str
    answer: str

    grounded: bool = Field(
        description="True if the answer is directly supported by "
                    "the source text"
    )


class QASet(BaseModel):
    qa_pairs: List[QAPair]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(raw: dict) -> List[Document]:
    """
    raw: the dict returned by loaders.load_source()

    Returns:
        List of LangChain Document objects with metadata.
    """

    source_type = raw["source_type"]

    if source_type == "youtube":

        # Transcripts are conversational.
        # Smaller chunks preserve spoken context.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n", ". ", " "],
        )

    elif source_type == "pdf":

        # Research papers usually contain denser paragraphs.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "],
        )

    else:

        # Web articles.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "],
        )

    chunks = splitter.split_text(raw["text"])

    docs = [
        Document(
            page_content=chunk,
            metadata={
                "source_type": source_type,
                "title": raw["title"],
                "chunk_index": i,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    return docs


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

def build_vectorstore(
    docs: List[Document],
    collection_name: str = "insight_extractor",
) -> Chroma:

    # Gemini is used ONLY for embeddings.
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

    # In-memory Chroma.
    # Fine for a single Streamlit session/demo.
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
    )

    return vectorstore


# ---------------------------------------------------------------------------
# Groq LLM helper
# ---------------------------------------------------------------------------

def get_llm(
    temperature: float = 0,
) -> ChatGroq:
    """
    Create the Groq language model used for
    summarization, Q&A, and chat.
    """

    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------

def summarize(
    docs: List[Document],
    llm: Optional[ChatGroq] = None,
) -> StructuredSummary:

    llm = llm or get_llm(temperature=0)

    parser = PydanticOutputParser(
        pydantic_object=StructuredSummary
    )

    # -----------------------------------------------------------------------
    # MAP STEP
    # -----------------------------------------------------------------------

    map_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Summarize the following excerpt in 2-3 sentences. "
            "Be factual and concise. Do not add information that is "
            "not present in the excerpt."
        ),
        (
            "user",
            "{chunk}"
        ),
    ])

    map_chain = (
        map_prompt
        | llm
        | StrOutputParser()
    )

    # Guard against very long sources.
    # At most approximately 20 chunks are sent directly to the LLM.
    chunks_to_map = (
        docs
        if len(docs) <= 20
        else docs[::max(1, len(docs) // 20)]
    )

    partial_summaries = []

    for d in chunks_to_map:

        summary = map_chain.invoke({
            "chunk": d.page_content
        })

        partial_summaries.append(summary)

    combined = "\n".join(partial_summaries)

    title = docs[0].metadata.get(
        "title",
        "Untitled source"
    )

    # -----------------------------------------------------------------------
    # REDUCE STEP
    # -----------------------------------------------------------------------

    reduce_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an analyst producing a structured brief "
            "from partial summaries of a source titled '{title}'. "
            "Base your output ONLY on the provided material. "
            "Do not invent facts.\n\n"
            "{format_instructions}"
        ),
        (
            "user",
            "Partial summaries:\n{combined}"
        ),
    ])

    reduce_chain = (
        reduce_prompt
        | llm
        | parser
    )

    result = reduce_chain.invoke({
        "title": title,
        "combined": combined,
        "format_instructions": parser.get_format_instructions(),
    })

    return result


# ---------------------------------------------------------------------------
# Auto-generated Q&A
# ---------------------------------------------------------------------------

def generate_qa(
    vectorstore: Chroma,
    title: str,
    n_questions: int = 6,
    llm: Optional[ChatGroq] = None,
) -> QASet:

    llm = llm or get_llm(temperature=0.3)

    parser = PydanticOutputParser(
        pydantic_object=QASet
    )

    # Retrieve chunks related to the source title.
    sample_docs = vectorstore.similarity_search(
        title,
        k=8,
    )

    context = "\n\n---\n\n".join(
        d.page_content
        for d in sample_docs
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Generate {n} likely reader questions about this source "
            "titled '{title}'. Answer each question ONLY using the "
            "provided context.\n\n"
            "If the context does not support an answer, mark "
            "grounded=false.\n\n"
            "Do not invent facts.\n\n"
            "{format_instructions}"
        ),
        (
            "user",
            "Context:\n{context}"
        ),
    ])

    chain = (
        prompt
        | llm
        | parser
    )

    result = chain.invoke({
        "n": n_questions,
        "title": title,
        "context": context,
        "format_instructions": parser.get_format_instructions(),
    })

    return result


# ---------------------------------------------------------------------------
# Follow-up Q&A / Chat
# ---------------------------------------------------------------------------

def answer_question(
    vectorstore: Chroma,
    question: str,
    k: int = 4,
    llm: Optional[ChatGroq] = None,
) -> dict:

    llm = llm or get_llm(temperature=0)

    # Retrieve the most relevant chunks.
    retrieved = vectorstore.similarity_search(
        question,
        k=k,
    )

    context_blocks = []

    for i, d in enumerate(retrieved):

        loc = _describe_location(
            d.metadata
        )

        context_blocks.append(
            f"[{i + 1}] ({loc})\n"
            f"{d.page_content}"
        )

    context = "\n\n".join(
        context_blocks
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Answer the user's question using ONLY the numbered "
            "context blocks below.\n\n"
            "Cite the block number(s) you used like [1], [2].\n\n"
            "If the context does not contain the answer, say so "
            "explicitly. Do not guess."
        ),
        (
            "user",
            "Context:\n{context}\n\n"
            "Question: {question}"
        ),
    ])

    chain = (
        prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke({
        "context": context,
        "question": question,
    })

    return {
        "answer": answer,

        "sources": [
            {
                "block": i + 1,
                "location": _describe_location(
                    d.metadata
                ),
                "excerpt": d.page_content[:200],
            }
            for i, d in enumerate(retrieved)
        ],
    }


# ---------------------------------------------------------------------------
# Source location description
# ---------------------------------------------------------------------------

def _describe_location(metadata: dict) -> str:

    if metadata.get("source_type") == "youtube":
        return (
            f"video, chunk "
            f"{metadata.get('chunk_index')}"
        )

    if metadata.get("source_type") == "pdf":
        return (
            f"paper, chunk "
            f"{metadata.get('chunk_index')}"
        )

    return (
        f"webpage, chunk "
        f"{metadata.get('chunk_index')}"
    )