"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError } from "@/lib/api/client";
import { getAnalysis, getResearch, queueAnalysis, retryAnalysis, type ImageAnalysis, type Research } from "@/lib/api/research";
import { dateFormat, sizeFormat } from "@/lib/utils/format";

const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const taskNames = ["classification", "detection", "ocr", "observation"] as const;

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const [item, setItem] = useState<Research | null>(null);
  const [analysis, setAnalysis] = useState<ImageAnalysis | null>(null);
  const [error, setError] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    const record = await getResearch(id);
    setItem(record);
    try {
      setAnalysis(await getAnalysis(id));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 404) setAnalysis(null);
      else throw cause;
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const record = await getResearch(id);
        if (!active) return;
        setItem(record);
        if (new URLSearchParams(window.location.search).has("queueError")) {
          setNotice("The research record was saved, but analysis could not be queued. You can retry from this page.");
        }
        try {
          const result = await getAnalysis(id);
          if (active) setAnalysis(result);
        } catch (cause) {
          if (cause instanceof ApiError && cause.status === 404) {
            if (active) setAnalysis(null);
          } else throw cause;
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Unable to load this research record.");
      }
    };
    void load();
    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    if (!analysis || !["queued", "processing"].includes(analysis.status)) return;
    let active = true;
    const timer = window.setInterval(() => {
      if (!active) return;
      void refresh().catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to refresh analysis status."); });
    }, 2500);
    return () => { active = false; window.clearInterval(timer); };
  }, [analysis, refresh]);

  async function queue() {
    setActionBusy(true); setError(""); setNotice("");
    try { await queueAnalysis(id); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to queue analysis."); }
    finally { setActionBusy(false); }
  }

  async function retry() {
    setActionBusy(true); setError("");
    try { await retryAnalysis(id); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to retry analysis."); }
    finally { setActionBusy(false); }
  }

  if (error && !item) return <div role="alert" className="alert">{error}</div>;
  if (!item) return <p role="status" className="muted">Loading research record…</p>;
  const imageUrl = `${apiBase}/api/v1/images/${encodeURIComponent(item.image_id)}/thumbnail?size=2400`;
  const analysisDimensions = analysis?.image_dimensions;

  return <>
    <div className="eyebrow">Research record · {item.id.slice(0, 8)}</div>
    <h1 className="page-title">{item.title}</h1>
    <p className="lead">Submitted {dateFormat(item.created_at)} · <span className={`status ${item.status}`}>{item.status}</span></p>
    {notice && <div className="alert" role="status">{notice}</div>}
    {error && <div className="alert" role="alert">{error}</div>}
    <section className="section grid-2">
      <div>
        <h2 className="section-title">Research overview</h2>
        <div className="info-row"><span className="info-label">Status</span><span><span className={`status ${item.status}`}>{item.status}</span></span></div>
        <div className="info-row"><span className="info-label">Image</span><span className="info-value">{item.image.original_filename}</span></div>
        <div className="info-row"><span className="info-label">Submitted</span><span>{dateFormat(item.created_at)}</span></div>
        {item.subject_name && <div className="info-row"><span className="info-label">Subject</span><span>{item.subject_name}</span></div>}
        {item.event_name && <div className="info-row"><span className="info-label">Event</span><span>{item.event_name}</span></div>}
        {item.organization && <div className="info-row"><span className="info-label">Organization</span><span>{item.organization}</span></div>}
        {item.public_profile_url && <div className="info-row"><span className="info-label">Public profile</span><a href={item.public_profile_url} target="_blank" rel="noreferrer">Open source link ↗</a></div>}
        {item.additional_context && <div className="info-row"><span className="info-label">Additional context</span><span>{item.additional_context}</span></div>}
      </div>
      <div>
        <h2 className="section-title" style={{ marginBottom: 14 }}>Image information</h2>
        <div className="panel">
          <div className="info-row"><span className="info-label">Dimensions</span><span>{item.image.width} × {item.image.height}</span></div>
          <div className="info-row"><span className="info-label">Format</span><span>{item.image.mime_type}</span></div>
          <div className="info-row"><span className="info-label">File size</span><span>{sizeFormat(item.image.file_size)}</span></div>
          <div className="info-row"><span className="info-label">SHA-256</span><span className="small">{item.image.sha256}</span></div>
        </div>
      </div>
    </section>

    <section className="section">
      <div className="section-head"><div><h2 className="section-title">Image preview</h2><p className="small muted">{analysis?.ocr?.blocks.length ? "Outlined regions correspond to extracted OCR words." : "Original uploaded image, orientation-corrected for viewing."}</p></div></div>
      <div className="analysis-image-wrap"><div className="analysis-image"><Image src={imageUrl} alt={`Uploaded image: ${item.image.original_filename}`} width={analysis?.image_dimensions?.width || item.image.width} height={analysis?.image_dimensions?.height || item.image.height} unoptimized />
        {analysisDimensions && analysis?.ocr?.blocks.map((block, index) => <span key={`${block.sequence}-${index}`} className="ocr-box" title={`${block.text}${block.confidence === null ? "" : ` · ${Math.round(block.confidence * 100)}%`}`} style={{ left: `${block.box.x / analysisDimensions.width * 100}%`, top: `${block.box.y / analysisDimensions.height * 100}%`, width: `${block.box.width / analysisDimensions.width * 100}%`, height: `${block.box.height / analysisDimensions.height * 100}%` }} />)}
      </div></div>
    </section>

    <section className="section">
      <div className="section-head"><div><h2 className="section-title">Image analysis</h2><p className="small muted">Local model predictions and OCR. Outputs can be incomplete or uncertain.</p></div>
        {!analysis && <button className="btn btn-primary" type="button" onClick={queue} disabled={actionBusy}>{actionBusy ? "Queueing…" : "Start image analysis"}</button>}
        {analysis?.status === "failed" && <button className="btn" type="button" onClick={retry} disabled={actionBusy}>{actionBusy ? "Retrying…" : "Retry analysis"}</button>}
      </div>
      {!analysis ? <p className="muted">No image analysis has been queued for this record.</p> : <>
        <div className="info-row"><span className="info-label">Analysis status</span><span className={`status ${analysis.status}`}>{analysis.status}</span></div>
        {analysis.status === "queued" || analysis.status === "processing" ? <p role="status" className="muted small">The local worker is {analysis.status}. This page checks for updates every few seconds.</p> : null}
        {analysis.error_code && <p role="alert" className="alert">Analysis could not complete ({analysis.error_code}). See model setup guidance in the documentation.</p>}
        {analysis.warning && <p className="alert">Partial results: {analysis.warning}</p>}
        <div className="grid-2" style={{ marginTop: 16 }}>
          <article className="panel"><h3 className="section-title">Image classification</h3>
            {analysis.classification ? <><p>{analysis.classification.category}</p><p className="small muted">Raw model score (not calibrated): {analysis.classification.confidence === null ? "not available" : `${Math.round(analysis.classification.confidence * 100)}%`} · {analysis.classification.model_name} {analysis.classification.model_version}</p>
              {analysis.classification.alternatives.length > 0 && <ul>{analysis.classification.alternatives.map((alt, index) => <li key={`${alt.category}-${index}`}>{alt.category}: {Math.round(alt.confidence * 100)}%</li>)}</ul>}</>
              : <p className="small muted">{analysis.task_statuses.classification === "failed" ? "Uncertain classification — no validated iSquare category model is available." : `Task ${analysis.task_statuses.classification}.`}</p>}
          </article>
          <article className="panel"><h3 className="section-title">People and objects</h3><p>{analysis.human_presence.message}</p>
            {analysis.detections.length ? <ul>{analysis.detections.map((d) => <li key={d.id}>{d.label} · {Math.round(d.confidence * 100)}% model confidence</li>)}</ul>
              : <p className="small muted">{analysis.task_statuses.detection === "failed" ? "Object detector unavailable." : `Task ${analysis.task_statuses.detection}.`}</p>}
          </article>
        </div>
        <article className="section panel"><h3 className="section-title">OCR text</h3>
          {analysis.ocr ? <><p className="small muted">{analysis.ocr.engine_name} {analysis.ocr.engine_version} · {analysis.ocr.language || "language unavailable"} · {analysis.ocr.duration_ms ?? "—"} ms</p>
            {analysis.ocr.text ? <pre className="ocr-text">{analysis.ocr.text}</pre> : <p className="muted">No readable text was returned.</p>}
            <details><summary>Text regions ({analysis.ocr.blocks.length})</summary><ol>{analysis.ocr.blocks.map((block, index) => <li key={`${block.sequence}-${index}`}>{block.text} <span className="muted small">{block.confidence === null ? "confidence unavailable" : `${Math.round(block.confidence * 100)}% model confidence`}</span></li>)}</ol></details>
          </> : <p className="muted">{analysis.task_statuses.ocr === "failed" ? "OCR could not run. Install Tesseract and the configured language pack to enable it." : `Task ${analysis.task_statuses.ocr}.`}</p>}
        </article>
        <div className="grid-2">
          <article className="panel"><h3 className="section-title">Visual observations</h3>{analysis.observations.length ? <ul>{analysis.observations.map((observation, index) => <li key={`${observation.evidence_reference}-${index}`}>{observation.description}<div className="small muted">Evidence: {observation.evidence_reference} · {observation.model_name} {observation.model_version}</div></li>)}</ul> : <p className="small muted">No evidence-backed observations were produced.</p>}</article>
          <article className="panel"><h3 className="section-title">Task and model details</h3><ul>{taskNames.map((task) => <li key={task}>{task}: {analysis.task_statuses[task]}</li>)}</ul><p className="small muted">Preprocessing: {analysis.preprocessing.join(", ") || "none reported"}</p>{analysis.executions.map((execution, index) => <p className="small muted" key={`${execution.task_type}-${index}`}>{execution.task_type}: {execution.model_name}{execution.model_version ? ` ${execution.model_version}` : ""} · {execution.duration_ms ?? "—"} ms{execution.error_code ? ` · ${execution.error_code}` : ""}</p>)}</article>
        </div>
      </>}
    </section>
  </>;
}
