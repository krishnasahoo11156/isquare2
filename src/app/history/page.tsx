"use client";

import { useEffect, useState } from "react";
import { getResearchList, type Research } from "@/lib/api/research";
import { ResearchTable } from "@/components/shared/ResearchTable";

const pageSize = 20;

export default function History() {
  const [items, setItems] = useState<Research[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getResearchList(pageSize, offset)
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setTotal(result.total);
      })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to load research history."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [offset]);

  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + items.length, total);
  function changePage(nextOffset: number) {
    setLoading(true);
    setError("");
    setOffset(nextOffset);
  }

  return <>
    <div className="eyebrow">Workspace</div>
    <h1 className="page-title">History</h1>
    <p className="lead">Research records created in this workspace.</p>
    <section className="section">
      {error ? <div role="alert" className="alert">{error}</div> : loading ? <p className="muted">Loading history…</p> : <>
        <ResearchTable items={items} />
        {total > pageSize && <div className="section-head" style={{ marginTop: 16 }}>
          <span className="small muted" aria-live="polite">Showing {first}–{last} of {total}</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn" type="button" onClick={() => changePage(Math.max(0, offset - pageSize))} disabled={offset === 0}>Previous</button>
            <button className="btn" type="button" onClick={() => changePage(offset + pageSize)} disabled={offset + pageSize >= total}>Next</button>
          </div>
        </div>}
      </>}
    </section>
  </>;
}
