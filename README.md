#  InsightLens — Multi-Source Insight & Q&A Generator

<p align="center">
  <b>Turn YouTube videos, research papers, web articles, and PDFs into structured insights and grounded answers.</b>
</p>

<p align="center">
  <a href="https://insightlenss.streamlit.app/">
    <img src="https://img.shields.io/badge/🚀%20Live%20Demo-InsightLens-FF4B4B?style=for-the-badge" alt="Live Demo">
  </a>
  <a href="https://github.com/yasaswitaraja/InsightLens">
    <img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
</p>
 
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white">
  <img src="https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=flat-square">
  <img src="https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square">
  <img src="https://img.shields.io/badge/Gemini-Embeddings-4285F4?style=flat-square&logo=google">
  <img src="https://img.shields.io/badge/Chroma-Vector%20DB-FF6F61?style=flat-square">
</p>

---

## 🌐 Live Application

### 🚀 [Try InsightLens Live](https://insightlenss.streamlit.app/)

Analyze a source and interact with it using AI-powered summarization and Retrieval-Augmented Generation (RAG).

**Supported sources:**

| Source | Supported |
|---|:---:|
| 🎥 YouTube Videos | ✅ |
| 📄 Research Papers / arXiv | ✅ |
| 🌐 Web Articles | ✅ |
| 📑 Local PDF Files | ✅ |

---

# 🧠 What is InsightLens?

**InsightLens** is a multi-source AI research assistant that converts long-form content into structured, searchable knowledge.

Instead of manually reading an entire paper, watching a long video, or going through a lengthy article, users can provide the source and InsightLens:

```text
SOURCE
  │
  ▼
EXTRACT CONTENT
  │
  ▼
CHUNK + PROCESS
  │
  ▼
GENERATE EMBEDDINGS
  │
  ▼
STORE IN VECTOR DATABASE
  │
  ▼
RETRIEVE RELEVANT CONTEXT
  │
  ▼
LLM
  │
  ├──► Structured Summary
  ├──► Key Points
  ├──► Claims & Evidence
  ├──► Limitations
  └──► Grounded Q&A
