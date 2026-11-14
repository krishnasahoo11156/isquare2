import { api } from "./client";

export type ResearchStatus = "queued" | "processing" | "completed" | "failed";

export type ImageAsset = {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number;
  height: number;
  sha256: string;
  created_at: string;
};

export type ImageMetadata = ImageAsset & {
  exif: Record<string, string>;
  provenance: string;
  ai_detection: string;
};

export type Research = {
  id: string;
  title: string;
  image_id: string;
  subject_name: string | null;
  event_name: string | null;
  organization: string | null;
  public_profile_url: string | null;
  additional_context: string | null;
  status: ResearchStatus;
  created_at: string;
  updated_at: string;
  image: ImageAsset;
};

export type ResearchList = {
  items: Research[];
  total: number;
  limit: number;
  offset: number;
};

export type AnalysisTaskStatus = "pending" | "processing" | "completed" | "failed" | "skipped";
export type AnalysisStatus = "queued" | "processing" | "completed" | "failed";
export type AnalysisBox = { x: number; y: number; width: number; height: number };
export type ImageAnalysis = {
  id: string;
  research_job_id: string;
  image_asset_id: string;
  status: AnalysisStatus;
  analysis_version: string;
  task_statuses: Record<"classification" | "detection" | "ocr" | "observation", AnalysisTaskStatus>;
  image_dimensions: { width: number; height: number } | null;
  preprocessing: string[];
  classification: { category: string; confidence: number | null; alternatives: { category: string; confidence: number }[]; model_name: string; model_version: string; duration_ms: number | null; status: AnalysisTaskStatus } | null;
  human_presence: { status: "detected" | "not_detected" | "unknown"; count: number | null; message: string };
  detections: { id: number; label: string; confidence: number; box: AnalysisBox; model_name: string; model_version: string }[];
  ocr: { text: string; language: string | null; engine_name: string; engine_version: string | null; duration_ms: number | null; status: AnalysisTaskStatus; blocks: { text: string; confidence: number | null; box: AnalysisBox; sequence: number }[] } | null;
  observations: { category: string; description: string; confidence: number | null; evidence_reference: string; model_name: string; model_version: string }[];
  executions: { task_type: string; model_name: string; model_version: string | null; status: AnalysisTaskStatus; duration_ms: number | null; error_code: string | null }[];
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  warning: string | null;
};

export type ResearchCreate = {
  image_id: string;
  subject_name?: string;
  event_name?: string;
  organization?: string;
  public_profile_url?: string;
  additional_context?: string;
};

export async function uploadImage(file: File): Promise<ImageAsset> {
  const body = new FormData();
  body.append("file", file);
  return api<ImageAsset>("/api/v1/images/upload", { method: "POST", body });
}

export function getImageMetadata(imageId: string): Promise<ImageMetadata> {
  return api<ImageMetadata>(`/api/v1/images/${encodeURIComponent(imageId)}/metadata`);
}

export function createResearch(payload: ResearchCreate): Promise<Research> {
  return api<Research>("/api/v1/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateResearchStatus(id: string, status: ResearchStatus): Promise<Research> {
  return api<Research>(`/api/v1/research/${encodeURIComponent(id)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export function getResearchList(limit = 20, offset = 0): Promise<ResearchList> {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return api<ResearchList>(`/api/v1/research?${query}`);
}

export function getResearch(id: string): Promise<Research> {
  return api<Research>(`/api/v1/research/${encodeURIComponent(id)}`);
}

export function queueAnalysis(id: string): Promise<{ analysis_id: string; research_job_id: string; status: AnalysisStatus; already_exists: boolean }> {
  return api(`/api/v1/research/${encodeURIComponent(id)}/analyze`, { method: "POST" });
}

export function retryAnalysis(id: string) {
  return api<{ analysis_id: string; research_job_id: string; status: AnalysisStatus; already_exists: boolean }>(`/api/v1/research/${encodeURIComponent(id)}/analysis/retry`, { method: "POST" });
}

export function getAnalysis(id: string): Promise<ImageAnalysis> {
  return api<ImageAnalysis>(`/api/v1/research/${encodeURIComponent(id)}/analysis`);
}
