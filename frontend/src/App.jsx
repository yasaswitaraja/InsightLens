import { useMemo, useState } from "react";
import {
  ArrowUp,
  BarChart3,
  Check,
  Clipboard,
  Download,
  FileText,
  Globe,
  Loader2,
  MessageSquare,
  Play,
  Plus,
  Search,
  Upload,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
const API_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");
const emptyResult = {
  source: null,
  sources: [],
  summary: "",
  key_points: [],
  findings: [],
  concepts: [],
  charts: [],
  chunk_count: 0,
};

function App() {
  const [mode, setMode] = useState("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(emptyResult);
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [compareUrls, setCompareUrls] = useState("");
  const [comparison, setComparison] = useState(null);
  const [compareBusy, setCompareBusy] = useState(false);

  const hasResult = Boolean(sessionId && result.source);
  const sourceLabel = useMemo(() => {
    if (!result.source) return "No source loaded";
    if (result.sources?.length > 1) return `${result.sources.length} sources`;
    if (result.source.type === "youtube") return "YouTube";
    if (result.source.type === "pdf") return "PDF document";
    return "Web article";
  }, [result]);

  async function parseResponse(response) {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "The server could not complete the request.");
    return body;
  }

  
function applyResult(data) {
  const insights = data.insights || {};

  const normalizedResult = {
    ...data,
    source: data.source || data.sources?.[0] || null,
    sources: data.sources || (data.source ? [data.source] : []),
    summary: insights.summary || data.summary || "",
    key_points: (insights.key_points || data.key_points || []).map(
      (item) => typeof item === "string" ? { text: item } : item
    ),
    findings: (
      insights.main_findings ||
      data.findings ||
      data.main_findings ||
      []
    ).map(
      (item) => typeof item === "string" ? { text: item } : item
    ),
    concepts: (
      insights.important_concepts ||
      data.concepts ||
      data.important_concepts ||
      []
    ).map(
      (item) => typeof item === "string" ? { text: item } : item
    ),
    charts: data.charts || [],
    chunk_count: data.chunk_count || 0,
  };

  setResult(normalizedResult);

  if (data.session_id) {
    setSessionId(data.session_id);
  }
}

  async function analyze() {
    setBusy(true);
    setError("");
    setMessages([]);
    setComparison(null);
    setResult(emptyResult);
    setSessionId("");
    try {
      let response;
      if (mode === "url") {
        if (!url.trim()) throw new Error("Enter a URL first.");
        const form = new FormData();
        form.append("url", url.trim());
        response = await fetch(`${API_URL}/api/analyze/url`, { method: "POST", body: form });
      } else {
        if (!file) throw new Error("Choose a PDF first.");
        const form = new FormData();
        form.append("file", file);
        response = await fetch(`${API_URL}/api/analyze/pdf`, { method: "POST", body: form });
      }
      applyResult(await parseResponse(response));
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function addSources() {
    if (!sessionId) return;
    const urls = compareUrls.split("\n").map((item) => item.trim()).filter(Boolean);
    if (!urls.length) {
      setError("Add at least one URL to compare.");
      return;
    }
    setCompareBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/add/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, urls }),
      });
      applyResult(await parseResponse(response));
      setCompareUrls("");
      setComparison(null);
    } catch (err) {
      setError(err.message || "Could not add the comparison source.");
    } finally {
      setCompareBusy(false);
    }
  }

  async function addPdfToWorkspace(event) {
    const selected = event.target.files?.[0];
    event.target.value = "";
    if (!selected || !sessionId) return;
    setCompareBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("session_id", sessionId);
      form.append("file", selected);
      const response = await fetch(`${API_URL}/api/add/pdf`, { method: "POST", body: form });
      applyResult(await parseResponse(response));
      setComparison(null);
    } catch (err) {
      setError(err.message || "Could not add the PDF.");
    } finally {
      setCompareBusy(false);
    }
  }

  async function compareSources() {
    if (!sessionId || result.sources?.length < 2) return;
    setCompareBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setComparison(await parseResponse(response));
    } catch (err) {
      setError(err.message || "Could not compare the sources.");
    } finally {
      setCompareBusy(false);
    }
  }

  async function askQuestion(event) {
    event?.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || !sessionId || busy) return;
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setQuestion("");
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question: trimmed }),
      });
      const data = await parseResponse(response);
      setMessages((current) => [...current, { role: "assistant", content: data.answer, evidence: data.evidence || [] }]);
    } catch (err) {
      setMessages((current) => [...current, { role: "assistant", content: `I couldn't answer that: ${err.message}`, evidence: [] }]);
    } finally {
      setBusy(false);
    }
  }

  async function exportPdf() {
  if (!sessionId) {
    alert("Analyze a source before exporting.");
    return;
  }

  try {
    const formData = new FormData();
    formData.append("session_id", sessionId);

    const response = await fetch(`${API_URL}/api/export/pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "PDF export failed.");
    }

    const pdfBlob = await response.blob();

    if (pdfBlob.type && !pdfBlob.type.includes("pdf")) {
      throw new Error("The server did not return a PDF file.");
    }

    const downloadUrl = window.URL.createObjectURL(pdfBlob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = "InsightLens-Research-Report.pdf";

    document.body.appendChild(link);
    link.click();
    link.remove();

    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("PDF export error:", error);
    alert(`Could not export PDF: ${error.message}`);
  }
}
  async function copyAnswer(content, index) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      window.setTimeout(() => setCopiedIndex(null), 1400);
    } catch {
      setError("Clipboard access was blocked by the browser.");
    }
  }

  function resetWorkspace() {
    setUrl("");
    setFile(null);
    setResult(emptyResult);
    setSessionId("");
    setQuestion("");
    setMessages([]);
    setError("");
    setComparison(null);
    setCompareUrls("");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">IL</div>
          <div><div className="brand-name">InsightLens</div><div className="brand-subtitle">Research workspace</div></div>
        </div>
        <button className="new-analysis" onClick={resetWorkspace}><Plus size={17} />New analysis</button>
        <div className="sidebar-section">
          <div className="sidebar-label">SOURCE</div>
          <button className={`source-option ${mode === "url" ? "active" : ""}`} onClick={() => setMode("url")}><Globe size={17} /><span>URL or YouTube</span></button>
          <button className={`source-option ${mode === "pdf" ? "active" : ""}`} onClick={() => setMode("pdf")}><FileText size={17} /><span>PDF document</span></button>
        </div>
        <div className="sidebar-bottom"><div className="system-note"><div className="system-dot" /><div><strong>InsightLens API</strong><span>RAG + evidence analysis</span></div></div></div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="mobile-brand"><div className="brand-mark">IL</div><strong>InsightLens</strong></div>
          {hasResult ? <div className="topbar-actions"><span className="source-pill"><span className="pill-dot" />{sourceLabel}</span><button className="outline-button" onClick={exportPdf}><Download size={16} />Export PDF</button></div> : <div className="topbar-status">AI research workspace</div>}
        </header>

        <div className={`workspace ${hasResult ? "has-result" : ""}`}>
          {!hasResult ? (
            <section className="welcome">
              <div className="welcome-copy">
                <div className="eyebrow">MULTI-SOURCE RESEARCH</div>
                <h1>Understand the source.<br />See the evidence.</h1>
                <p>Analyze YouTube videos, web articles, research papers, and PDFs. InsightLens extracts structured findings, keeps source evidence, and answers questions from retrieved context.</p>
              </div>
              <div className="input-card">
                <div className="input-tabs">
                  <button className={mode === "url" ? "selected" : ""} onClick={() => setMode("url")}><Globe size={16} />URL / YouTube</button>
                  <button className={mode === "pdf" ? "selected" : ""} onClick={() => setMode("pdf")}><FileText size={16} />PDF</button>
                </div>
                {mode === "url" ? <div className="url-input-row"><div className="input-icon"><Search size={18} /></div><input value={url} onChange={(event) => setUrl(event.target.value)} onKeyDown={(event) => event.key === "Enter" && analyze()} placeholder="Paste a YouTube, article, or research URL" autoComplete="off" /><button className="orange-button" onClick={analyze} disabled={busy}>{busy ? <><Loader2 size={16} className="spin" />Analyzing</> : <>Analyze<ArrowUp size={16} /></>}</button></div> : <div className="upload-area"><label className="file-picker"><Upload size={20} /><strong>{file ? file.name : "Choose a PDF"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "PDF files up to 20 MB"}</span><input type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="orange-button" onClick={analyze} disabled={busy}>{busy ? <><Loader2 size={16} className="spin" />Analyzing</> : <>Analyze PDF<ArrowUp size={16} /></>}</button></div>}
              </div>
              {error && <div className="error-banner">{error}</div>}
            </section>
          ) : (
            <>
              <div className="result-layout">
                <section className="source-column">
                  <div className="source-header"><div><div className="eyebrow">ANALYZED SOURCES</div><h2>{result.sources?.length > 1 ? `${result.sources.length} sources in workspace` : result.source.name}</h2></div><button className="icon-button" onClick={resetWorkspace}><X size={17} /></button></div>

                  {result.source.type === "youtube" && result.source.video_id && <YouTubePanel source={result.source} />}

                  <div className="source-meta"><div className="meta-item"><span>Sources</span><strong>{result.sources?.length || 1}</strong></div><div className="meta-item"><span>Searchable chunks</span><strong>{result.chunk_count}</strong></div></div>

                  <div className="source-list">
                    {(result.sources || [result.source]).map((source, index) => <SourceRow key={`${source.name}-${index}`} source={source} />)}
                  </div>

                  <div className="source-actions"><button className="outline-button" onClick={exportPdf}><Download size={16} />Download full report</button></div>

                  <ComparisonPanel compareUrls={compareUrls} setCompareUrls={setCompareUrls} addSources={addSources} addPdfToWorkspace={addPdfToWorkspace} compareSources={compareSources} compareBusy={compareBusy} sourceCount={result.sources?.length || 1} />
                </section>

                <section className="insights-column">
                  <div className="insights-heading"><div><div className="eyebrow">SOURCE INSIGHTS</div><h2>Research overview</h2></div></div>
                  <InsightCard title="Executive summary" text={result.summary} />
                  <EvidenceListCard title="Key points" items={result.key_points} />
                  <EvidenceListCard title="Main findings" items={result.findings} confidence />
                  <EvidenceListCard title="Important concepts" items={result.concepts} />
                  {comparison && <ComparisonResult comparison={comparison} />}
                  {error && <div className="error-banner">{error}</div>}
                </section>
              </div>

              <section className="chat-section">
                <div className="chat-heading"><div><div className="eyebrow">GROUNDED Q&A</div><h2>Ask about the evidence</h2></div><MessageSquare size={18} /></div>
                <div className="chat-box">
                  {messages.length === 0 ? <div className="chat-empty"><div className="chat-empty-icon"><MessageSquare size={18} /></div><div><strong>Ask a question about the analyzed sources.</strong><span>Answers include source evidence when the retrieved context supports them.</span></div></div> : <div className="messages">{messages.map((message, index) => <Message key={`${message.role}-${index}`} message={message} index={index} copiedIndex={copiedIndex} copyAnswer={copyAnswer} />)}</div>}
                  <form className="chat-input-row" onSubmit={askQuestion}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask anything about the analyzed sources..." disabled={busy} /><button className="send-button" type="submit" disabled={!question.trim() || busy}>{busy ? <Loader2 size={17} className="spin" /> : <ArrowUp size={17} />}</button></form>
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function YouTubePanel({ source }) {
  const videoId = source?.video_id;

  const thumbnailUrl = videoId
    ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`
    : null;

  const watchUrl =
    source?.watch_url ||
    (videoId
      ? `https://www.youtube.com/watch?v=${videoId}`
      : source?.url);

  return (
    <div className="youtube-panel">
      <div className="youtube-preview">
        {thumbnailUrl ? (
          <a
            href={watchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="youtube-thumbnail-link"
            aria-label="Watch analyzed YouTube video"
          >
            <img
              src={thumbnailUrl}
              alt={source?.title || "Analyzed YouTube video"}
              className="youtube-thumbnail"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />

            <span className="youtube-play-button">
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="currentColor"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            </span>
          </a>
        ) : (
          <div className="youtube-thumbnail-fallback">
            Video preview unavailable
          </div>
        )}
      </div>

      <div className="youtube-panel-footer">
        <div className="youtube-source-info">
          <strong>YouTube source</strong>
          <span>Transcript processed</span>
        </div>

        {watchUrl && (
          <a
            href={watchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="youtube-open-link"
          >
            <span>▶</span> Open in YouTube
          </a>
        )}
      </div>
    </div>
  );
}

function SourceRow({ source }) {
  return <div className="source-row"><div className={`source-type ${source.type}`}>{source.type === "youtube" ? <Play size={13} /> : source.type === "pdf" ? <FileText size={13} /> : <Globe size={13} />}</div><div className="source-row-text"><strong>{source.name}</strong><span>{source.type}{source.video_id ? " · timestamp evidence available" : ""}</span></div>{source.url && <a href={source.url} target="_blank" rel="noreferrer">Open</a>}</div>;
}

function ComparisonPanel({ compareUrls, setCompareUrls, addSources, addPdfToWorkspace, compareSources, compareBusy, sourceCount }) {
  return <article className="insight-card comparison-panel"><div className="card-heading"><div><h3>Compare sources</h3><p className="card-subtitle">Add another URL or PDF, then compare the evidence.</p></div><span>{sourceCount}</span></div><textarea value={compareUrls} onChange={(event) => setCompareUrls(event.target.value)} placeholder="Paste one or more URLs, one per line" /><div className="comparison-actions"><button className="orange-button small" onClick={addSources} disabled={compareBusy}><Plus size={14} />Add URLs</button><label className="outline-button small-file"><Upload size={14} />Add PDF<input type="file" accept="application/pdf,.pdf" onChange={addPdfToWorkspace} /></label>{sourceCount > 1 && <button className="outline-button" onClick={compareSources} disabled={compareBusy}>{compareBusy ? <Loader2 size={14} className="spin" /> : <BarChart3 size={14} />}Compare</button>}</div></article>;
}

function InsightCard({ title, text }) {
  return <article className="insight-card"><div className="card-heading"><h3>{title}</h3></div><div className="summary-text">{text.split("\n").map((paragraph, index) => paragraph.trim() ? <p key={index}>{paragraph}</p> : null)}</div></article>;
}

function EvidenceListCard({ title, items, confidence }) {
  return <article className="insight-card"><div className="card-heading"><h3>{title}</h3><span>{items.length}</span></div>{items.length ? <div className="evidence-list">{items.map((item, index) => <div className="evidence-item" key={`${title}-${index}`}><div className="evidence-text">{item.text}</div>{confidence && item.confidence != null && <div className="confidence">Confidence {Math.round(item.confidence * 100)}%</div>}<EvidenceLinks ids={item.evidence || []} details={item.evidence_details || []} /></div>)}</div> : <p className="muted">No separate items were extracted.</p>}</article>;
}

function EvidenceLinks({ ids, details = [] }) {
  if (!ids.length) return null;
  const detailById = Object.fromEntries(details.map((item) => [item.id, item]));
  return <div className="evidence-links">{ids.map((id) => {
    const detail = detailById[id];
    const href = detail?.timestamp_url || detail?.source;
    const location = detail?.timestamp ? ` · ${detail.timestamp}` : detail?.page != null ? ` · page ${Number(detail.page) + 1}` : "";
    return href ? <a key={id} className="evidence-chip" href={href} target="_blank" rel="noreferrer" title={detail?.excerpt || "Source evidence"}>{id}{location}</a> : <span key={id} className="evidence-chip">{id}</span>;
  })}</div>;
}

function VisualizationCard({ charts }) {
  if (!charts?.length) return <article className="insight-card visualization-card"><div className="card-heading"><h3>Automatic visualization</h3></div><p className="muted">No reliable numeric dataset was detected in this source.</p></article>;
  const chart = charts[0];
  return <article className="insight-card visualization-card"><div className="card-heading"><div><h3>{chart.title}</h3><p className="card-subtitle">Automatically detected from source data</p></div><BarChart3 size={17} /></div><MiniChart chart={chart} /></article>;
}

function MiniChart({ chart }) {
  const values = chart.data.map((item) => item.value);
  const max = Math.max(...values, 1);
  return <div className="mini-chart">{chart.data.map((item) => <div className="chart-row" key={item.label}><span>{item.label}</span><div className="chart-track"><div className="chart-bar" style={{ width: `${Math.max(4, (item.value / max) * 100)}%` }} /></div><strong>{formatNumber(item.value)}</strong></div>)}</div>;
}

function formatNumber(value) {
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function ComparisonResult({ comparison }) {
  return <article className="insight-card comparison-result"><div className="card-heading"><h3>Source comparison</h3></div><p className="summary-text">{comparison.overview}</p><ComparisonSection title="Where sources agree" items={comparison.agreements} /><ComparisonSection title="Key differences" items={comparison.differences} /><ComparisonSection title="Missing information" items={comparison.missing_information} /></article>;
}

function ComparisonSection({ title, items }) {
  if (!items?.length) return null;
  return <div className="comparison-section"><strong>{title}</strong><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div>;
}


function Message({ message, index, copiedIndex, copyAnswer }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        <div className="message-role">
          {message.role === "user" ? "You" : "InsightLens"}
        </div>

        <div className="message-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {String(message.content ?? "")}
          </ReactMarkdown>
        </div>

        {message.role === "assistant" && (
          <>
            <button
              className="copy-button"
              onClick={() => copyAnswer(message.content, index)}
              title="Copy answer"
            >
              {copiedIndex === index ? (
                <Check size={14} />
              ) : (
                <Clipboard size={14} />
              )}
            </button>

            {message.evidence?.length > 0 && (
              <div className="answer-evidence">
                <span>Evidence</span>
                {message.evidence.map((item) => (
                  <a
                    key={item.id}
                    href={item.timestamp_url || item.source}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {item.id}
                    {item.timestamp
                      ? ` · ${item.timestamp}`
                      : item.page != null
                      ? ` · page ${Number(item.page) + 1}`
                      : ""}
                  </a>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
