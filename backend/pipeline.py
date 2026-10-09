
import io
import json
import os
import re
import unicodedata
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from langchain_huggingface import HuggingFaceEmbeddings

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

from loaders import (
    extract_video_id,
    format_timestamp,
    get_youtube_transcript,
    load_pdf_documents,
    load_url_documents,
    youtube_timestamp_url,
    youtube_watch_url,
)


class InsightEngine:
    def __init__(self):
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError(
                "GROQ_API_KEY is not configured on the backend."
            )

        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError(
                "GEMINI_API_KEY is not configured on the backend."
            )

        self.llm = ChatGroq(
            model=os.getenv(
                "GROQ_MODEL",
                "openai/gpt-oss-120b",
            ),
            temperature=0,
            max_tokens=1800,
        )

        self.embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

        self.vector_store = None
        self.sources = []
        self.chunks = []
        self.summary = ""
        self.key_points = []
        self.findings = []
        self.concepts = []
        self.charts = []
        self.qa_history = []
        self.comparison = None

    @property
    def primary_source(self):
        return self.sources[0] if self.sources else None

    @staticmethod
    def _clean_report_text(value):
        """Normalize text before displaying or exporting it."""
        if value is None:
            return ""
        text = str(value)

    # Replace common Unicode punctuation with PDF-safe equivalents.
        replacements = {
            "\u2010": "-",  # hyphen
            "\u2011": "-",  # non-breaking hyphen
            "\u2012": "-",  # figure dash
            "\u2013": "-",  # en dash
            "\u2014": "-",  # em dash
            "\u2212": "-",  # minus sign
            "\u25a0": "-",  # black square
            "\u25aa": "-",  # small black square
            "\u2022": "-",  # bullet
            "\u00a0": " ",  # non-breaking space
            "\ufeff": "",   # byte-order mark
        }

        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)

        # Normalize Unicode characters consistently.
        text = unicodedata.normalize("NFKC", text)
        

        # Remove control characters while preserving whitespace.
        text = "".join(
            char
            for char in text
            if char in "\n\t" or unicodedata.category(char)[0] != "C"
        )
         # Ensure remaining text is compatible with ReportLab's Helvetica font.
        text = text.encode("cp1252", errors="replace").decode("cp1252")

        return text

    def _rebuild_vector_store(self):
        if not self.chunks:
            raise RuntimeError("No readable content is available.")

        # Rebuild using the complete chunk list so newly added sources
        # are included in retrieval.
        self.vector_store = Chroma.from_documents(
            documents=self.chunks,
            embedding=self.embeddings,
        )

    def _chunk_documents(
        self,
        documents: list[Document],
        source_index: int,
    ):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=180,
        )

        raw_chunks = splitter.split_documents(documents)
        output = []

        for index, document in enumerate(raw_chunks, start=1):
            metadata = dict(document.metadata)

            metadata["chunk_id"] = f"S{source_index}-C{index}"
            metadata["source_index"] = source_index
            metadata.setdefault("source_type", "unknown")

            output.append(
                Document(
                    page_content=document.page_content,
                    metadata=metadata,
                )
            )

        return output

    def _source_record(
        self,
        name,
        source_type,
        url=None,
        video_id=None,
        transcript_status=None,
    ):
        return {
            "name": name,
            "type": source_type,
            "url": url,
            "video_id": video_id,
            "watch_url": (
                youtube_watch_url(video_id)
                if video_id
                else None
            ),
            "embed_url": (
                f"https://www.youtube-nocookie.com/embed/{video_id}"
                if video_id
                else None
            ),
            "thumbnail_url": (
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                if video_id
                else None
            ),
            "transcript_status": transcript_status,
        }

    def _add_documents(
        self,
        documents,
        source_name,
        source_type,
        source_url=None,
        video_id=None,
        transcript_status=None,
    ):
        if not documents:
            raise RuntimeError(
                "No readable content was found in the source."
            )

        source_index = len(self.sources) + 1
        chunks = self._chunk_documents(documents, source_index)

        if not chunks:
            raise RuntimeError(
                "The source did not produce searchable text chunks."
            )

        # Avoid leaving partially updated source state if embedding
        # or analysis fails.
        old_sources = list(self.sources)
        old_chunks = list(self.chunks)
        old_vector_store = self.vector_store

        self.sources.append(
            self._source_record(
                source_name,
                source_type,
                source_url,
                video_id,
                transcript_status,
            )
        )

        self.chunks.extend(chunks)

        try:
            self._rebuild_vector_store()
            self._generate_insights()
            self._generate_charts()
        except Exception:
            self.sources = old_sources
            self.chunks = old_chunks
            self.vector_store = old_vector_store
            raise

        return self.result()

    def analyze_url(self, url: str):
        url = url.strip()

        if not url:
            raise RuntimeError("Please enter a URL.")

        normalized_url = (
            url
            if url.startswith(("http://", "https://"))
            else f"https://{url}"
        )

        parsed = urlparse(normalized_url)

        if not parsed.netloc:
            raise RuntimeError(
                "Please enter a complete URL, including https://."
            )

        video_id = extract_video_id(normalized_url)

        if video_id:
            documents, transcript_status = get_youtube_transcript(
                normalized_url
            )

            if not documents:
                raise RuntimeError(
                    "The YouTube URL is valid, but captions could not "
                    "be retrieved. Try a video with accessible captions."
                )

            return self._add_documents(
                documents,
                f"YouTube video {video_id}",
                "youtube",
                youtube_watch_url(video_id),
                video_id,
                transcript_status,
            )

        documents = load_url_documents(normalized_url)

        return self._add_documents(
            documents,
            normalized_url,
            "web",
            normalized_url,
        )

    def analyze_pdf(self, content: bytes, filename: str):
        documents = load_pdf_documents(content, filename)

        return self._add_documents(
            documents,
            filename,
            "pdf",
        )

    def add_url(self, url: str):
        return self.analyze_url(url)

    def add_pdf(self, content: bytes, filename: str):
        return self.analyze_pdf(content, filename)

    def _evidence_text(self, documents: list[Document]) -> str:
        blocks = []

        for index, doc in enumerate(documents, start=1):
            metadata = doc.metadata
            source = metadata.get("source", "Unknown source")

            location = (
                metadata.get("timestamp")
                or metadata.get("page")
            )

            location_text = (
                f" | Location: {location}"
                if location is not None
                else ""
            )

            blocks.append(
                f"[E{index}] Source: {source}{location_text}\n"
                f"{doc.page_content[:1800]}"
            )

        return "\n\n".join(blocks)

    @staticmethod
    def _parse_json(text: str):
        """Parse a JSON response without assuming the model is perfect."""
        if not text or not text.strip():
            return None

        cleaned = text.strip()

        cleaned = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\s*```\s*$",
            "",
            cleaned,
        )

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try extracting an object from surrounding text.
        start = cleaned.find("{")

        if start != -1:
            decoder = json.JSONDecoder()

            try:
                result, _ = decoder.raw_decode(cleaned[start:])
                return result
            except json.JSONDecodeError:
                pass

        # Also support a JSON array as the complete response.
        start = cleaned.find("[")

        if start != -1:
            decoder = json.JSONDecoder()

            try:
                result, _ = decoder.raw_decode(cleaned[start:])
                return result
            except json.JSONDecodeError:
                pass

        return None

    def _generate_insights(self):
        # Limit prompt size; keep all chunks in Chroma for Q&A.
        evidence_docs = self.chunks[:12]
        evidence = self._evidence_text(evidence_docs)[:10500]

        prompt = f"""
You are the InsightLens research analysis engine.

Use ONLY the supplied evidence. Never invent facts.

Return one valid JSON object and nothing else.
Do not use Markdown fences.
Use double quotes for JSON keys and string values.
Do not include trailing commas or unescaped line breaks inside strings.

Required structure:
{{
  "summary": "Two to four concise paragraphs.",
  "key_points": [
    {{"text": "A supported point", "evidence": ["E1"]}}
  ],
  "findings": [
    {{
      "text": "A supported finding",
      "evidence": ["E1"],
      "confidence": 0.8
    }}
  ],
  "concepts": [
    {{"text": "A supported concept", "evidence": ["E1"]}}
  ]
}}

Rules:
- Every item must cite valid evidence IDs from the supplied evidence.
- Confidence must be a number between 0 and 1.
- Keep each item concise.
- Do not invent facts, statistics, trends, or conclusions.
- If the evidence is insufficient, return an empty list for that category.
- Do not describe a chart unless the evidence contains actual data.

EVIDENCE:
{evidence}
"""

        response = self.llm.invoke(prompt)
        raw = response.content

        if not isinstance(raw, str):
            raw = str(raw)

        data = self._parse_json(raw)

        if not isinstance(data, dict):
            # Do not display malformed JSON as a successful summary.
            raise RuntimeError(
                "The AI returned invalid JSON for the research analysis. "
                "Please retry the analysis. If this repeats, inspect the "
                "raw model response in the backend logs."
            )

        self.summary = str(data.get("summary", "")).strip()

        self.key_points = self._normalise_items(
            data.get("key_points")
        )

        self.findings = self._normalise_items(
            data.get("findings"),
            include_confidence=True,
        )

        self.concepts = self._normalise_items(
            data.get("concepts")
        )

        for item in (
            self.key_points
            + self.findings
            + self.concepts
        ):
            item["evidence_details"] = self._evidence_lookup(
                item.get("evidence", [])
            )

    @staticmethod
    def _normalise_items(items, include_confidence=False):
        result = []

        if not isinstance(items, list):
            return result

        for item in items:
            if isinstance(item, str):
                result.append({
                    "text": item.strip(),
                    "evidence": [],
                    "confidence": None,
                })
                continue

            if not isinstance(item, dict) or not item.get("text"):
                continue

            evidence = item.get("evidence", [])

            if not isinstance(evidence, list):
                evidence = []

            confidence = (
                item.get("confidence")
                if include_confidence
                else None
            )

            try:
                confidence = (
                    max(0.0, min(1.0, float(confidence)))
                    if confidence is not None
                    else None
                )
            except (TypeError, ValueError):
                confidence = None

            result.append({
                "text": str(item["text"]).strip(),
                "evidence": [
                    str(value)
                    for value in evidence
                    if re.fullmatch(r"E\d+", str(value))
                ],
                "confidence": confidence,
            })

        return result

    def _generate_charts(self):
        """
        Detect explicit year/value pairs only.

        Examples:
            2021: 20
            2022 - $28M
            2023 | 41%

        At least three unique data points are required.
        """
        text = "\n".join(
            doc.page_content
            for doc in self.chunks
        )

        pattern = (
            r"\b((?:19|20)\d{2})\b\s*"
            r"(?::|\||-)\s*"
            r"([$€£₹]?\s*\d+(?:[,.]\d+)?\s*[KMBkmb%]?)"
        )

        matches = re.findall(pattern, text)

        points = []
        seen = set()

        for year, raw_value in matches:
            value_text = raw_value.replace(",", "").strip()

            numeric = re.search(
                r"\d+(?:\.\d+)?",
                value_text,
            )

            if not numeric:
                continue

            value = float(numeric.group(0))
            suffix = value_text[-1:].upper()

            if suffix == "K":
                value *= 1_000
            elif suffix == "M":
                value *= 1_000_000
            elif suffix == "B":
                value *= 1_000_000_000

            key = (year, value)

            if key in seen:
                continue

            seen.add(key)
            points.append({
                "label": year,
                "value": value,
            })

        if len(points) < 3:
            self.charts = []
            return

        self.charts = [{
            "type": "line",
            "title": "Detected trend",
            "x_label": "Year",
            "y_label": "Value",
            "data": points[:12],
            "source": (
                self.sources[0]["name"]
                if self.sources
                else "Source"
            ),
            "automatic": True,
        }]

    def _evidence_lookup(self, evidence_ids):
        lookup = {}

        for index, doc in enumerate(self.chunks[:30], start=1):
            lookup[f"E{index}"] = doc

        result = []

        for evidence_id in evidence_ids or []:
            doc = lookup.get(evidence_id)

            if doc is None:
                continue

            metadata = doc.metadata

            result.append({
                "id": evidence_id,
                "source": metadata.get(
                    "source",
                    "Unknown source",
                ),
                "source_type": metadata.get("source_type"),
                "page": metadata.get("page"),
                "timestamp": metadata.get("timestamp"),
                "timestamp_url": metadata.get("timestamp_url"),
                "excerpt": doc.page_content[:420].strip(),
            })

        return result

    def result(self):
        return {
            "source": self.primary_source,
            "sources": self.sources,
            "summary": self.summary,
            "key_points": self.key_points,
            "findings": self.findings,
            "concepts": self.concepts,
            "charts": self.charts,
            "chunk_count": len(self.chunks),
        }

    def ask(self, question: str):
        if not self.vector_store:
            raise RuntimeError("No source is loaded.")

        cleaned_question = question.strip()

        if not cleaned_question:
            raise RuntimeError("Please enter a question.")

        docs = self.vector_store.similarity_search(
            cleaned_question,
            k=5,
        )

        if not docs:
            raise RuntimeError(
                "No relevant source content was retrieved."
            )

        context = self._evidence_text(docs)

        prompt = f"""
You are a grounded research assistant.

Answer using ONLY the evidence below.

Cite supporting evidence inline using [E1], [E2], etc.
Only use evidence IDs present in this context.
If the answer is unsupported, say the information is not
available in the analyzed sources.

EVIDENCE:
{context}

QUESTION:
{cleaned_question}
"""

        answer = self.llm.invoke(prompt).content.strip()
        evidence = []

        for index, doc in enumerate(docs, start=1):
            evidence_id = f"E{index}"

            if f"[{evidence_id}]" not in answer:
                continue

            metadata = doc.metadata

            evidence.append({
                "id": evidence_id,
                "source": metadata.get(
                    "source",
                    "Unknown source",
                ),
                "page": metadata.get("page"),
                "timestamp": metadata.get("timestamp"),
                "timestamp_url": metadata.get("timestamp_url"),
                "excerpt": doc.page_content[:420].strip(),
            })

        history_item = {
            "question": cleaned_question,
            "answer": answer,
            "evidence": evidence,
        }

        self.qa_history.append(history_item)

        return history_item

    def compare(self):
        if len(self.sources) < 2:
            raise RuntimeError(
                "Add at least two sources before comparing them."
            )

        evidence = self._evidence_text(self.chunks[:40])

        source_names = "\n".join(
            f"S{index + 1}: {source['name']}"
            for index, source in enumerate(self.sources)
        )

        prompt = f"""
Compare the following sources using only the supplied evidence.

Return one valid JSON object, without Markdown fences:
{{
  "overview": "...",
  "agreements": ["..."],
  "differences": ["..."],
  "source_positions": [
    {{"source": "S1", "summary": "..."}}
  ],
  "missing_information": ["..."]
}}

Every statement must be supported by the evidence.
Do not invent claims. Keep the result concise.

SOURCES:
{source_names}

EVIDENCE:
{evidence}
"""

        response = self.llm.invoke(prompt)
        data = self._parse_json(response.content)

        if not isinstance(data, dict):
            raise RuntimeError(
                "The comparison response was not valid JSON. "
                "Please retry the comparison."
            )

        self.comparison = data
        return data

    def export_pdf(self) -> bytes:
        """Export the current research results as a formatted PDF."""
        buffer = io.BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=22 * mm,
            bottomMargin=20 * mm,
            title="InsightLens Research Report",
            author="InsightLens",
        )

        charcoal = colors.HexColor("#20242C")
        orange = colors.HexColor("#F28C28")
        muted = colors.HexColor("#626B78")
        light_grey = colors.HexColor("#F2F4F7")
        border_grey = colors.HexColor("#D8DDE5")

        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            name="ILTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=29,
            alignment=TA_LEFT,
            textColor=charcoal,
            spaceAfter=7,
        ))

        styles.add(ParagraphStyle(
            name="ILSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=muted,
            spaceAfter=12,
        ))

        styles.add(ParagraphStyle(
            name="ILSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=charcoal,
            spaceBefore=13,
            spaceAfter=7,
            keepWithNext=True,
        ))

        styles.add(ParagraphStyle(
            name="ILBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=charcoal,
            spaceAfter=7,
            wordWrap="LTR",
        ))

        styles.add(ParagraphStyle(
            name="ILSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=muted,
            spaceAfter=4,
            wordWrap="LTR",
        ))

        styles.add(ParagraphStyle(
            name="ILTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ))

        styles.add(ParagraphStyle(
            name="ILTableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=charcoal,
            wordWrap="LTR",
        ))

        def safe_text(value):
            return escape(self._clean_report_text(value))

        def paragraph(value, style="ILBody"):
            return Paragraph(safe_text(value), styles[style])

        def add_section(story, heading):
            story.append(Spacer(1, 4))
            story.append(
                Paragraph(
                    safe_text(heading),
                    styles["ILSection"],
                )
            )
            story.append(HRFlowable(
                width="100%",
                thickness=1.2,
                color=orange,
                spaceAfter=8,
            ))

        def add_bullets(story, items):
            if not items:
                story.append(
                    paragraph("No items available.", "ILSmall")
                )
                return

            for item in items:
                if isinstance(item, str):
                    text = item
                    evidence_ids = []
                    confidence = None
                elif isinstance(item, dict):
                    text = item.get("text", "")
                    evidence_ids = item.get("evidence", []) or []
                    confidence = item.get("confidence")
                else:
                    continue

                cleaned = self._clean_report_text(text)

                if not cleaned:
                    continue

                details = []

                if confidence is not None:
                    try:
                        details.append(
                            f"Confidence: "
                            f"{round(float(confidence) * 100)}%"
                        )
                    except (TypeError, ValueError):
                        pass

                if evidence_ids:
                    details.append(
                        "Evidence: " + ", ".join(
                            str(value) for value in evidence_ids
                        )
                    )

                story.append(KeepTogether([
                    paragraph("• " + cleaned),
                    paragraph(
                        " | ".join(details),
                        "ILSmall",
                    ) if details else Spacer(1, 2),
                ]))

        story = []

        story.append(
            Paragraph(
                "InsightLens",
                styles["ILTitle"],
            )
        )

        story.append(
            Paragraph(
                "RESEARCH REPORT  |  AI-ASSISTED SOURCE ANALYSIS",
                styles["ILSubtitle"],
            )
        )

        story.append(HRFlowable(
            width="100%",
            thickness=2,
            color=orange,
            spaceAfter=12,
        ))

        # Source overview.
        add_section(story, "Source Overview")

        story.append(
            paragraph(f"Sources analyzed: {len(self.sources)}")
        )
        story.append(
            paragraph(f"Searchable text chunks: {len(self.chunks)}")
        )

        source_rows = [[
            Paragraph("TYPE", styles["ILTableHeader"]),
            Paragraph("SOURCE", styles["ILTableHeader"]),
            Paragraph("DETAIL", styles["ILTableHeader"]),
        ]]

        for source in self.sources:
            source_type = safe_text(
                source.get("type", "Unknown").upper()
            )
            source_name = safe_text(
                source.get("name", "Unnamed source")
            )
            source_url = safe_text(source.get("url") or "—")

            source_rows.append([
                Paragraph(source_type, styles["ILTableCell"]),
                Paragraph(source_name, styles["ILTableCell"]),
                Paragraph(source_url, styles["ILTableCell"]),
            ])

        if len(source_rows) > 1:
            source_table = Table(
                source_rows,
                colWidths=[25 * mm, 58 * mm, 79 * mm],
                repeatRows=1,
                hAlign="LEFT",
            )

            source_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), charcoal),
                ("GRID", (0, 0), (-1, -1), 0.35, border_grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    light_grey,
                ]),
            ]))

            story.append(source_table)

        # Summary.
        add_section(story, "Executive Summary")

        if self.summary.strip():
            for block in re.split(r"\n\s*\n", self.summary.strip()):
                if block.strip():
                    story.append(paragraph(block))
        else:
            story.append(
                paragraph("No summary is available.", "ILSmall")
            )

        # Key points, findings and concepts.
        add_section(story, "Key Points")
        add_bullets(story, self.key_points)

        add_section(story, "Main Findings")
        add_bullets(story, self.findings)

        add_section(story, "Important Concepts")
        add_bullets(story, self.concepts)

        # Only display charts generated from explicit data.
        if self.charts:
            add_section(story, "Detected Data")

            for chart in self.charts:
                story.append(
                    paragraph(
                        chart.get("title", "Data table"),
                    )
                )

                chart_data = chart.get("data", [])

                rows = [[
                    Paragraph("LABEL", styles["ILTableHeader"]),
                    Paragraph("VALUE", styles["ILTableHeader"]),
                ]]

                for point in chart_data:
                    rows.append([
                        Paragraph(
                            safe_text(point.get("label", "")),
                            styles["ILTableCell"],
                        ),
                        Paragraph(
                            safe_text(point.get("value", "")),
                            styles["ILTableCell"],
                        ),
                    ])

                if len(rows) > 1:
                    chart_table = Table(
                        rows,
                        colWidths=[65 * mm, 45 * mm],
                        repeatRows=1,
                    )

                    chart_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), charcoal),
                        ("GRID", (0, 0), (-1, -1), 0.35, border_grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                            colors.white,
                            light_grey,
                        ]),
                    ]))

                    story.append(chart_table)
                    story.append(Spacer(1, 8))

        # Question-answer history.
        if self.qa_history:
            add_section(story, "Questions and Answers")

            for item in self.qa_history:
                question = self._clean_report_text(
                    item.get("question", "")
                )
                answer = self._clean_report_text(
                    item.get("answer", "")
                )

                story.append(KeepTogether([
                    paragraph("Question: " + question),
                    paragraph("Answer: " + answer),
                ]))

                evidence = item.get("evidence", [])

                if evidence:
                    story.append(
                        paragraph(
                            "Supporting evidence: "
                            + ", ".join(
                                str(entry.get("id", ""))
                                for entry in evidence
                            ),
                            "ILSmall",
                        )
                    )

                story.append(Spacer(1, 5))

        # Source comparison, when requested.
        if isinstance(self.comparison, dict):
            add_section(story, "Source Comparison")

            overview = self.comparison.get("overview", "")
            if overview:
                story.append(paragraph(overview))

            for key, title in (
                ("agreements", "Agreements"),
                ("differences", "Differences"),
                ("missing_information", "Missing Information"),
            ):
                values = self.comparison.get(key, [])
                if values:
                    story.append(
                        Paragraph(
                            safe_text(title),
                            styles["Heading3"],
                        )
                    )
                    add_bullets(story, values)

            positions = self.comparison.get("source_positions", [])
            if positions:
                story.append(
                    Paragraph(
                        "Source Positions",
                        styles["Heading3"],
                    )
                )
                add_bullets(
                    story,
                    [
                        {
                            "text": (
                                str(entry.get("source", "Source"))
                                + ": "
                                + str(entry.get("summary", ""))
                            )
                        }
                        for entry in positions
                        if isinstance(entry, dict)
                    ],
                )

        def draw_page(canvas, doc):
            canvas.saveState()

            width, height = A4

            canvas.setStrokeColor(orange)
            canvas.setLineWidth(2)
            canvas.line(
                doc.leftMargin,
                height - 12 * mm,
                width - doc.rightMargin,
                height - 12 * mm,
            )

            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(muted)

            canvas.drawString(
                doc.leftMargin,
                10 * mm,
                "InsightLens | Research Report",
            )

            canvas.drawRightString(
                width - doc.rightMargin,
                10 * mm,
                f"Page {doc.page}",
            )

            canvas.restoreState()

        document.build(
            story,
            onFirstPage=draw_page,
            onLaterPages=draw_page,
        )

        return buffer.getvalue()