"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ImageUploader } from "@/components/research/ImageUploader";
import { createResearch, queueAnalysis, uploadImage, type ResearchCreate } from "@/lib/api/research";

const contextFields = ["subject_name", "event_name", "organization", "public_profile_url", "additional_context"] as const;

export default function NewResearch() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("");
  const [startAnalysis, setStartAnalysis] = useState(true);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select an image before starting research.");
      return;
    }
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      setStage("Uploading and validating image…");
      const image = await uploadImage(file);
      setStage("Creating research record…");
      const payload: ResearchCreate = { image_id: image.id };
      for (const key of contextFields) {
        const value = String(form.get(key) || "").trim();
        if (value) payload[key] = value;
      }
      const record = await createResearch(payload);
      if (startAnalysis) {
        setStage("Queueing local image analysis…");
        try {
          await queueAnalysis(record.id);
        } catch {
          router.push(`/research/${record.id}?queueError=1`);
          return;
        }
      }
      router.push(`/research/${record.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error. Please try again.");
    } finally {
      setBusy(false);
      setStage("");
    }
  }

  return <>
    <div className="heading-row"><div>
      <div className="eyebrow">New submission</div>
      <h1 className="page-title">Start a research record</h1>
      <p className="lead">Add an image and any context you already have.</p>
    </div></div>
    <form onSubmit={submit}>
      <div className="grid-2">
        <section>
          <h2 className="section-title" style={{ marginBottom: 14 }}>Image</h2>
          <ImageUploader onChange={setFile} />
          <p className="small muted">The file is checked and stored locally by the iSquare backend.</p>
        </section>
        <section>
          <h2 className="section-title">Context <span className="muted" style={{ fontWeight: 400 }}>(optional)</span></h2>
          <div className="field"><label htmlFor="subject_name">Subject name, if known</label><input id="subject_name" name="subject_name" maxLength={255} /></div>
          <div className="field"><label htmlFor="event_name">Event or conference</label><input id="event_name" name="event_name" maxLength={255} /></div>
          <div className="field"><label htmlFor="organization">Organization</label><input id="organization" name="organization" maxLength={255} /></div>
          <div className="field"><label htmlFor="public_profile_url">Public profile URL</label><input id="public_profile_url" name="public_profile_url" type="url" placeholder="https://" /></div>
          <div className="field"><label htmlFor="additional_context">Additional context</label><textarea id="additional_context" name="additional_context" maxLength={5000} placeholder="What would be useful to know about this image?" /></div>
        </section>
      </div>
      <section className="section panel">
        <h2 className="section-title">Potential research sources</h2>
        <p className="small muted">Source connections will only be used when authorized and implemented.</p>
        <div className="checks">{["Public websites", "Professional profiles", "Research publications", "News sources", "Public repositories"].map((source) =>
          <label className="check" key={source}><input type="checkbox" disabled aria-label={`${source} source not yet available`} />{source}<span className="muted">· future</span></label>)}</div>
      </section>
      <section className="section">
        <label className="check"><input type="checkbox" checked={startAnalysis} onChange={(event) => setStartAnalysis(event.target.checked)} />Queue CPU image analysis after the research record is created</label>
        <p className="small muted" style={{ marginTop: 6 }}>Analysis runs in the separate local worker. Optional model engines may report unavailable until installed.</p>
      </section>
      {error && <div role="alert" className="alert">{error}</div>}
      {stage && <p role="status" className="muted small">{stage}</p>}
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 22 }}>
        <button className="btn btn-primary" type="submit" disabled={busy || !file}>{busy ? "Working…" : startAnalysis ? "Create and queue analysis" : "Create research record"}</button>
      </div>
    </form>
  </>;
}
