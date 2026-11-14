"use client";

import { useState } from "react";
import { ImageUploader } from "@/components/research/ImageUploader";
import { getImageMetadata, uploadImage, type ImageMetadata } from "@/lib/api/research";
import { sizeFormat } from "@/lib/utils/format";

export default function Forensics() {
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState<ImageMetadata | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function inspect() {
    if (!file) return;
    setError("");
    setBusy(true);
    setData(null);
    try {
      const uploaded = await uploadImage(file);
      setData(await getImageMetadata(uploaded.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to inspect the image.");
    } finally {
      setBusy(false);
    }
  }

  return <>
    <div className="eyebrow">Image workspace</div>
    <h1 className="page-title">Image forensics</h1>
    <p className="lead">Inspect file properties and available metadata.</p>
    <section className="section grid-2">
      <div>
        <ImageUploader onChange={(next) => { setFile(next); setData(null); setError(""); }} />
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-primary" disabled={!file || busy} onClick={inspect}>
            {busy ? "Inspecting…" : "Inspect image"}
          </button>
        </div>
        {busy && <p role="status" className="small muted">Uploading image and reading available metadata…</p>}
        {error && <div className="alert" role="alert">{error}</div>}
      </div>
      <div>
        <h2 className="section-title" style={{ marginBottom: 14 }}>Image information</h2>
        {data ? <div className="panel">
          {[["File", data.original_filename], ["Format", data.mime_type], ["Dimensions", `${data.width} × ${data.height}`], ["File size", sizeFormat(data.file_size)], ["SHA-256", data.sha256]].map(([key, value]) =>
            <div className="info-row" key={key}><span className="info-label">{key}</span><span className="info-value small">{value}</span></div>)}
        </div> : <p className="small muted">Choose an image and inspect it to view verified file information.</p>}
      </div>
    </section>
    {data && <>
      <section className="section">
        <h2 className="section-title">EXIF information</h2>
        <div className="panel" style={{ marginTop: 12 }}>
          {Object.keys(data.exif).length ? Object.entries(data.exif).map(([key, value]) =>
            <div className="info-row" key={key}><span className="info-label">{key}</span><span>{value}</span></div>)
            : <p className="small muted">No EXIF fields found.</p>}
        </div>
      </section>
      <section className="section grid-2">
        <div className="panel"><h2 className="section-title">Provenance</h2><p className="small muted">{data.provenance}</p></div>
        <div className="panel"><h2 className="section-title">AI-generated image detection</h2><p className="small muted">{data.ai_detection}</p></div>
      </section>
    </>}
  </>;
}
