"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Plus } from "lucide-react";
import { api } from "@/lib/api/client";
import { getResearchList, type Research } from "@/lib/api/research";
import { ResearchTable } from "@/components/shared/ResearchTable";

export default function Dashboard() {
  const [items, setItems] = useState<Research[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [service, setService] = useState<"checking" | "available" | "unavailable">("checking");
  const [analysisCounts, setAnalysisCounts] = useState({ completed_analyses: 0, queued_analyses: 0, processing_analyses: 0, failed_analyses: 0 });

  useEffect(() => {
    getResearchList(5).then((data) => { setItems(data.items); setTotal(data.total); })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load research records."))
      .finally(() => setLoading(false));
    api<{ status: string }>("/api/v1/health").then(() => setService("available")).catch(() => setService("unavailable"));
    api<typeof analysisCounts & { total_research: number }>("/api/v1/analysis/summary").then(setAnalysisCounts).catch(() => undefined);
  }, []);

  return <>
    <div className="heading-row"><div>
      <div className="eyebrow">Visual intelligence workspace</div>
      <h1 className="page-title">Research, grounded in evidence.</h1>
      <p className="lead">Submit an image to start a structured research record.</p>
    </div><Link className="btn btn-primary" href="/research/new"><Plus />New Research</Link></div>
    <div className="stat-row" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
      <div className="stat"><span className="small muted">Research records</span><strong>{loading ? "—" : total}</strong></div>
      <div className="stat"><span className="small muted">Completed analyses</span><strong>{analysisCounts.completed_analyses}</strong></div>
      <div className="stat"><span className="small muted">Queued / processing</span><strong>{analysisCounts.queued_analyses + analysisCounts.processing_analyses}</strong></div>
      <div className="stat"><span className="small muted">Failed analyses</span><strong>{analysisCounts.failed_analyses}</strong></div>
    </div>
    <section className="section">
      <div className="section-head"><h2 className="section-title">Recent research</h2><Link href="/history" className="small muted">View history <ArrowRight size={13} style={{ verticalAlign: "-2px" }} /></Link></div>
      {error ? <div className="alert" role="alert">{error}</div> : loading ? <p className="muted">Loading research records…</p> : <ResearchTable items={items} />}
    </section>
    <section className="section panel">
      <div className="section-head"><h2 className="section-title">System status</h2><span className="status">{service === "checking" ? "Checking service…" : service === "available" ? "API available" : "API unavailable"}</span></div>
      <p className="muted small">{service === "available" ? "Image intake, research records, and the analysis queue are responding. Optional OCR and vision model dependencies are configured separately." : service === "unavailable" ? "The backend could not be reached. Start the FastAPI service to use image intake and record storage." : "Checking the backend connection…"}</p>
    </section>
  </>;
}
