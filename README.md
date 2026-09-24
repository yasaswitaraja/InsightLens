#  InsightLens

### Multi-Source AI Research & Q&A Assistant

<p align="center">
  <strong>Transform YouTube videos, research papers, web articles, and PDFs into structured insights and grounded answers using Retrieval-Augmented Generation.</strong>
</p>

<p align="center">
  <a href="https://insightlenss.streamlit.app/">
    <img src="https://img.shields.io/badge/🚀%20LIVE%20DEMO-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  </a>
  <a href="https://github.com/yasaswitaraja/InsightLens">
    <img src="https://img.shields.io/badge/💻%20SOURCE%20CODE-181717?style=for-the-badge&logo=github&logoColor=white" />
  </a>
</p> 

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=flat-square" />
  <img src="https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square" />
  <img src="https://img.shields.io/badge/Gemini-Embeddings-4285F4?style=flat-square&logo=google" />
  <img src="https://img.shields.io/badge/Chroma-Vector%20DB-FF6F61?style=flat-square" />
</p>

---

## 🌐 Live Demo

<p align="center">
  <a href="https://insightlenss.streamlit.app/">
    <img src="https://img.shields.io/badge/OPEN%20INSIGHTLENS-Click%20Here-FF4B4B?style=for-the-badge" />
  </a>
</p>

> **InsightLens** turns long-form information into searchable knowledge and lets users ask questions directly against the processed source.

---

# ✦ What is InsightLens?

**InsightLens** is an AI-powered research assistant built around a **Retrieval-Augmented Generation (RAG)** architecture.

It accepts information from multiple sources:

<table>
<tr>
<td align="center" width="25%">

### 🎥

**YouTube**

Videos & Transcripts

</td>

<td align="center" width="25%">

### 📄

**Research**

arXiv & Papers

</td>

<td align="center" width="25%">

### 🌐

**Web**

Online Articles

</td>

<td align="center" width="25%">

### 📑

**PDF**

Local Documents

</td>
</tr>
</table>

The application extracts the content, converts it into searchable vector representations, retrieves relevant information, and uses an LLM to generate responses grounded in the source.

---

# ⚡ Core Capabilities

<table>
<tr>
<td width="50%">

### 🧠 AI Summarization

Convert lengthy sources into concise, structured summaries.

</td>
<td width="50%">

### 🔎 Semantic Search

Find relevant information based on meaning rather than exact keywords.

</td>
</tr>

<tr>
<td width="50%">

### 💬 Grounded Q&A

Ask questions about the source and receive context-aware answers.

</td>
<td width="50%">

### 📚 Multi-Source Processing

Process YouTube, PDFs, web pages, and research papers.

</td>
</tr>

<tr>
<td width="50%">

### 📊 Structured Insights

Extract key points, claims, evidence, and limitations.

</td>
<td width="50%">

### 🧪 QA Evaluation

Evaluate generated responses using an integrated evaluation pipeline.

</td>
</tr>
</table>

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │        USER          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    STREAMLIT UI      │
                         │                      │
                         │ YouTube • PDF • Web  │
                         │ arXiv • Questions    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                   ┌────────────────────────────────┐
                   │         SOURCE LOADERS         │
                   │                                │
                   │ YouTube │ PDF │ Web │ arXiv   │
                   └────────────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  TEXT PROCESSING     │
                         │                      │
                         │ Cleaning             │
                         │ Chunking             │
                         │ Metadata             │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  GEMINI EMBEDDINGS   │
                         │                      │
                         │ Text → Vectors       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   CHROMA VECTOR DB   │
                         │                      │
                         │ Semantic Retrieval   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   RETRIEVAL LAYER    │
                         │                      │
                         │ Relevant Chunks      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      GROQ LLM        │
                         │                      │
                         │ Context + Question   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                ┌──────────────────────────────────────┐
                │            INSIGHTLENS OUTPUT        │
                │                                      │
                │  Summary │ Key Points │ Evidence    │
                │  Claims  │ Limitations │ Q&A        │
                └──────────────────────────────────────┘
```

---

# 🔄 RAG Pipeline

InsightLens follows a complete Retrieval-Augmented Generation workflow:

```text
┌─────────────┐
│   SOURCE    │
│             │
│ YouTube     │
│ PDF         │
│ Web         │
│ arXiv       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   EXTRACT   │
│   CONTENT   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    CHUNK    │
│    TEXT     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   EMBED     │
│    TEXT     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CHROMA    │
│ VECTOR DB   │
└──────┬──────┘
       │
       │
       │     USER QUESTION
       │           │
       │           ▼
       │    ┌─────────────┐
       └───►│   RETRIEVE  │
            │   RELEVANT  │
            │   CONTEXT   │
            └──────┬──────┘
                   │
                   ▼
            ┌─────────────┐
            │  GROQ LLM   │
            │             │
            │ Context +   │
            │ Question    │
            └──────┬──────┘
                   │
                   ▼
            ┌─────────────┐
            │   ANSWER    │
            │             │
            │ Grounded &  │
            │ Structured  │
            └─────────────┘
```

---

# 🧠 How RAG Works

Instead of sending a user's question directly to an LLM:

```text
Question
   ↓
LLM
   ↓
Answer
```

InsightLens first retrieves information from the user's source:

```text
Question
   ↓
Question Embedding
   ↓
Semantic Search
   ↓
Relevant Source Chunks
   ↓
Context + Question
   ↓
Groq LLM
   ↓
Grounded Answer
```

This allows the application to generate answers using information retrieved from the provided source.

---

# 🔬 Processing Pipeline

### 01 — Source Ingestion

The user provides one of the supported sources.

```text
YouTube URL
Research Paper
Web Article
PDF File
```

↓

### 02 — Content Extraction

The appropriate loader extracts the source content and converts it into text.

↓

### 03 — Chunking

Large documents are divided into smaller chunks so relevant sections can be retrieved efficiently.

↓

### 04 — Embedding

Each chunk is converted into a numerical vector using the embedding model.

```text
Text Chunk
    ↓
Gemini Embedding Model
    ↓
Vector Representation
```

↓

### 05 — Vector Storage

Embeddings and their associated metadata are stored in **Chroma**.

↓

### 06 — Semantic Retrieval

When the user asks a question, the question is embedded and compared against stored vectors.

↓

### 07 — Context Construction

The most relevant chunks are selected and combined with the user's question.

↓

### 08 — LLM Generation

The context is sent to the **Groq-powered LLM**, which generates the final response.

↓

### 09 — Structured Output

The user receives:

```text
✓ Summary
✓ Key Points
✓ Claims & Evidence
✓ Limitations
✓ Grounded Q&A
```

---

# 🛠️ Technology Stack

<table>
<tr>
<th>Technology</th>
<th>Purpose</th>
</tr>

<tr>
<td><b>Python</b></td>
<td>Core application and AI pipeline</td>
</tr>

<tr>
<td><b>Streamlit</b></td>
<td>Interactive web interface</td>
</tr>

<tr>
<td><b>LangChain</b></td>
<td>Document processing and RAG workflow</td>
</tr>

<tr>
<td><b>Groq</b></td>
<td>Fast LLM inference</td>
</tr>

<tr>
<td><b>Gemini Embeddings</b></td>
<td>Text-to-vector representation</td>
</tr>

<tr>
<td><b>Chroma</b></td>
<td>Vector storage and similarity search</td>
</tr>

<tr>
<td><b>PyPDF</b></td>
<td>PDF text extraction</td>
</tr>

</table>

---

# 📁 Project Structure

```text
InsightLens/
│
├── app.py
│
├── loaders.py
│
├── pipeline.py
│
├── qa_eval.py
│
├── requirements.txt
│
├── .env
│
├── .gitignore
│
└── README.md
```

### `app.py`

Main Streamlit application.

Responsible for:

* User interface
* Source selection
* File uploads
* URL inputs
* Question input
* Displaying generated results

### `loaders.py`

Handles source-specific document ingestion.

```text
YouTube
   │
PDF ──────► loaders.py
   │
Web
   │
arXiv
```

### `pipeline.py`

Contains the core AI/RAG workflow:

```text
Documents
   ↓
Chunking
   ↓
Embeddings
   ↓
Chroma
   ↓
Retrieval
   ↓
LLM
   ↓
Response
```

### `qa_eval.py`

Contains functionality for evaluating generated question-answer responses.

---

# 💡 Example Use Cases

### Research

Upload a research paper and quickly identify:

* Research problem
* Methodology
* Dataset
* Results
* Limitations
* Future work

### Education

Use a YouTube lecture as a searchable knowledge source and ask questions about specific concepts.

### Technical Documentation

Process long technical documents and retrieve information through natural-language questions.

### Knowledge Extraction

Convert lengthy articles and documents into structured insights instead of manually reading the entire source.

---

# 🔐 API Key Security

API keys are loaded through environment variables rather than being hard-coded.

```env
GROQ_API_KEY=your_api_key
GEMINI_API_KEY=your_api_key
```

The `.env` file should **never be committed to GitHub**.

Recommended `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
.venv/
chroma/
```

---

# 📈 Future Enhancements

```text
┌─────────────────────────────────────┐
│          Future Improvements         │
├─────────────────────────────────────┤
│                                     │
│  • Source citations                 │
│  • Page-level references            │
│  • Multi-document comparison        │
│  • Hybrid search                    │
│  • Reranking                        │
│  • Conversation memory              │
│  • Persistent vector storage        │
│  • PDF/Markdown export              │
│  • Advanced evaluation metrics      │
│  • Additional document formats      │
│                                     │
└─────────────────────────────────────┘
```

---

# 🎯 Project Objective

The objective of InsightLens is to demonstrate a practical implementation of modern AI technologies by combining:

```text
Document Processing
        +
Text Embeddings
        +
Vector Databases
        +
Semantic Retrieval
        +
Retrieval-Augmented Generation
        +
Large Language Models
```

The project demonstrates how unstructured information can be transformed into a searchable knowledge system capable of producing context-aware responses.

---

# 📚 Skills Demonstrated

<p align="center">

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/RAG-412991?style=for-the-badge" />
<img src="https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge" />
<img src="https://img.shields.io/badge/LLM-Generative%20AI-8A2BE2?style=for-the-badge" />
<img src="https://img.shields.io/badge/Vector%20Database-Chroma-FF6F61?style=for-the-badge" />

<br>

<img src="https://img.shields.io/badge/Embeddings-4285F4?style=for-the-badge&logo=google&logoColor=white" />
<img src="https://img.shields.io/badge/Semantic%20Search-FF6F00?style=for-the-badge" />
<img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
<img src="https://img.shields.io/badge/AI%20Application%20Development-000000?style=for-the-badge" />

</p>

---

# 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yasaswitaraja/InsightLens.git
cd InsightLens
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment

**Windows:**

```bash
venv\Scripts\activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 6. Run the application

```bash
streamlit run app.py
```

The application will open locally in your browser.

---

# 🌐 Deployment

The application is deployed using **Streamlit Community Cloud**.

### Live Application

**https://insightlenss.streamlit.app/**

---

# 👨‍💻 Author

<p align="center">

<strong>InsightLens</strong><br>
Designed, developed, and maintained by <strong>Yasaswita Raja</strong>

<br><br>

<a href="https://github.com/yasaswitaraja">
<img src="https://img.shields.io/badge/GitHub-yasaswitaraja-181717?style=for-the-badge&logo=github&logoColor=white" />
</a>

<a href="https://www.linkedin.com/in/yasaswita-raja/">
<img src="https://img.shields.io/badge/LinkedIn-Yasaswita%20Raja-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" />
</a>

</p>

---

<p align="center">
  <sub>InsightLens — Turning information into searchable knowledge.</sub>
</p>

<p align="center">
  <strong>© 2026 Yasaswita Raja. All rights reserved.</strong>
</p>
