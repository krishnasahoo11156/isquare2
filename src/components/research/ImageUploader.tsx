"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { ImageUp, Trash2 } from "lucide-react";

const validTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

export function ImageUploader({ onChange }: { onChange: (file: File | null) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function pickFile(next?: File) {
    if (!next) return;
    if (!validTypes.has(next.type) || next.size > 10 * 1024 * 1024) {
      setFile(null);
      setPreviewUrl("");
      onChange(null);
      setError(!validTypes.has(next.type) ? "Choose a JPEG, PNG, or WEBP image." : "The image must be 10 MB or smaller.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setError("");
    setFile(next);
    setPreviewUrl(URL.createObjectURL(next));
    onChange(next);
  }

  function removeFile() {
    setFile(null);
    setPreviewUrl("");
    setError("");
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return <>
    <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(event) => pickFile(event.target.files?.[0])} />
    <div className="dropzone"
      onDragOver={(event) => { event.preventDefault(); event.currentTarget.classList.add("drag"); }}
      onDragLeave={(event) => event.currentTarget.classList.remove("drag")}
      onDrop={(event) => { event.preventDefault(); event.currentTarget.classList.remove("drag"); pickFile(event.dataTransfer.files[0]); }}>
      {file && previewUrl ? <div>
        <Image className="preview" src={previewUrl} width={1000} height={700} unoptimized alt={`Preview of ${file.name}`} />
        <div style={{ marginTop: 12 }}>
          <span className="small">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</span>{" "}
          <button className="btn" type="button" onClick={removeFile} aria-label="Remove image"><Trash2 size={14} />Remove</button>
        </div>
      </div> : <div>
        <ImageUp className="drop-icon" aria-hidden="true" />
        <strong>Choose an image to begin</strong>
        <p>JPEG, PNG, or WEBP · Up to 10 MB</p>
        <button type="button" className="btn" onClick={() => inputRef.current?.click()}>Browse files</button>
        <div className="small muted" style={{ marginTop: 10 }}>or drop an image here</div>
      </div>}
    </div>
    {error && <p role="alert" style={{ color: "#a33", fontSize: 12 }}>{error}</p>}
  </>;
}
