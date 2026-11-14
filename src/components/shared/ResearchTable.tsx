"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import type { Research } from "@/lib/api/research";
import { dateFormat } from "@/lib/utils/format";

function Thumbnail({ item }: { item: Research }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <span className="thumb-fallback" role="img" aria-label={`No preview available for ${item.title}`}>No preview</span>;
  return <Image className="thumb" src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/images/${item.image_id}/thumbnail`} alt={`Thumbnail for ${item.title}`} width={44} height={44} unoptimized onError={() => setFailed(true)} />;
}

export function ResearchTable({ items }: { items: Research[] }) {
  if (!items.length) return <div className="empty">
    <strong>No research records yet</strong>Your submitted research will appear here.
    <div style={{ marginTop: 16 }}><Link className="btn" href="/research/new">Start new research</Link></div>
  </div>;

  return <div className="table-wrap"><table className="table">
    <thead><tr><th>Research</th><th>Image</th><th>Submitted</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
    <tbody>{items.map((item) => <tr key={item.id}>
      <td><Link href={`/research/${item.id}`}><strong>{item.title}</strong></Link><div className="small muted">{item.id.slice(0, 8)}</div></td>
      <td><Thumbnail item={item} /></td>
      <td>{dateFormat(item.created_at)}</td>
      <td><span className={`status ${item.status}`}>{item.status}</span></td>
      <td><Link className="small" href={`/research/${item.id}`}>Open →</Link></td>
    </tr>)}</tbody>
  </table></div>;
}
