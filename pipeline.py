import os

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_chroma import Chroma

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)


# ============================================================
# MODELS
# ============================================================

def get_llm():

    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0
    )


def get_embeddings():

    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )


# ============================================================
# TEXT SPLITTER
# ============================================================

def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    return splitter.split_documents(documents)


# ============================================================
# VECTOR DATABASE
# ============================================================

def create_vector_store(documents):

    embeddings = get_embeddings()

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings
    )

    return vector_store


# ============================================================
# LLM RESPONSE
# ============================================================

def generate_summary(text):

    llm = get_llm()

    prompt = f"""
You are an expert research assistant.

Analyze the following content.

Provide:

1. A concise summary
2. Important key points
3. Main findings
4. Important concepts

Content:

{text}
"""

    response = llm.invoke(prompt)

    return response.content


# ============================================================
# QUESTION ANSWERING
# ============================================================

def answer_question(
    question,
    vector_store
):

    llm = get_llm()

    docs = vector_store.similarity_search(
        question,
        k=4
    )

    context = "\n\n".join(
        document.page_content
        for document in docs
    )

    prompt = f"""
You are a grounded question-answering assistant.

Answer the user's question using ONLY the provided context.

If the answer is not available in the context,
say that the information is not available in the source.

Context:

{context}

Question:

{question}
"""

    response = llm.invoke(prompt)

    return response.content


# ============================================================
# PROCESS SOURCE
# ============================================================

def process_source(
    source,
    source_type="url"
):

    # This function should call your existing loaders
    # depending on the source type.

    from loaders import load_source

    documents = load_source(
        source,
        source_type
    )

    chunks = split_documents(documents)

    vector_store = create_vector_store(chunks)

    # Combine text for initial summary
    text = "\n\n".join(
        doc.page_content
        for doc in chunks[:10]
    )

    summary = generate_summary(text)

    return {
        "summary": summary,
        "chunks": chunks,
        "vector_store": vector_store
    }