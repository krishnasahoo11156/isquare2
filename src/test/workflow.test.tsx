import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createElement, type ComponentProps } from "react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/layout/AppShell";
import { ImageUploader } from "@/components/research/ImageUploader";
import { ResearchTable } from "@/components/shared/ResearchTable";
import Dashboard from "@/app/page";
import Forensics from "@/app/forensics/page";
import History from "@/app/history/page";
import NewResearch from "@/app/research/new/page";
import Results from "@/app/research/[id]/page";
import { ApiError } from "@/lib/api/client";
import { createResearch, getAnalysis, getImageMetadata, getResearch, getResearchList, queueAnalysis, retryAnalysis, uploadImage } from "@/lib/api/research";
import type { ImageAnalysis, ImageAsset, ImageMetadata, Research } from "@/lib/api/research";

const { pushMock, apiMock } = vi.hoisted(() => ({ pushMock: vi.fn(), apiMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ id: "research-1" }),
}));

vi.mock("next/image", () => ({
  default: ({ unoptimized, ...props }: ComponentProps<"img"> & { unoptimized?: boolean }) => {
    void unoptimized;
    return createElement("img", { ...props, alt: props.alt ?? "" });
  },
}));

vi.mock("@/lib/api/client", () => ({
  api: apiMock,
  ApiError: class ApiError extends Error { constructor(message: string, public status: number) { super(message); } },
}));

vi.mock("@/lib/api/research", () => ({
  uploadImage: vi.fn(),
  createResearch: vi.fn(),
  getImageMetadata: vi.fn(),
  getResearch: vi.fn(),
  getResearchList: vi.fn(),
  updateResearchStatus: vi.fn(),
  queueAnalysis: vi.fn(), getAnalysis: vi.fn(), retryAnalysis: vi.fn(),
}));

const image: ImageAsset = {
  id: "image-1", original_filename: "sample.jpg", mime_type: "image/jpeg", file_size: 2048,
  width: 32, height: 24, sha256: "a".repeat(64), created_at: "2026-11-13T10:00:00+00:00",
};
const research: Research = {
  id: "research-1", title: "Conference image", image_id: image.id, subject_name: "Alex Example",
  event_name: "Research Day", organization: "Institute", public_profile_url: "https://example.org/profile",
  additional_context: "Panel speaker", status: "queued", created_at: image.created_at,
  updated_at: image.created_at, image,
};
const metadata: ImageMetadata = {
  ...image, exif: { ImageDescription: "Sample metadata" }, provenance: "No provenance manifest was detected or checked.", ai_detection: "Not yet analyzed",
};
const analysisResult: ImageAnalysis = {
  id: "analysis-1", research_job_id: research.id, image_asset_id: image.id, status: "completed", analysis_version: "v1",
  task_statuses: { classification: "failed", detection: "failed", ocr: "completed", observation: "completed" },
  image_dimensions: { width: 32, height: 24 }, preprocessing: ["exif_orientation_normalized", "grayscale"], classification: null,
  human_presence: { status: "unknown", count: null, message: "Person detection unavailable." }, detections: [],
  ocr: { text: "hello", language: "eng", engine_name: "Tesseract", engine_version: "5", duration_ms: 8, status: "completed", blocks: [{ text: "hello", confidence: 0.9, box: { x: 2, y: 3, width: 20, height: 8 }, sequence: 0 }] },
  observations: [{ category: "text", description: "OCR returned 1 readable word block.", confidence: null, evidence_reference: "ocr_result", model_name: "Tesseract", model_version: "5" }],
  executions: [], started_at: image.created_at, completed_at: image.created_at, error_code: null,
  warning: "Some analysis tasks were unavailable or failed: classification:classifier_not_configured, detection:detector_not_configured",
};

function fileInput(container: HTMLElement) {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Image file input was not rendered");
  return input;
}

beforeEach(() => {
  apiMock.mockImplementation((path: string) => Promise.resolve(path.includes("summary")
    ? { total_research: 1, completed_analyses: 0, queued_analyses: 0, processing_analyses: 0, failed_analyses: 0 }
    : { status: "ok" }));
  vi.mocked(uploadImage).mockResolvedValue(image);
  vi.mocked(createResearch).mockResolvedValue(research);
  vi.mocked(queueAnalysis).mockResolvedValue({ analysis_id: "analysis-1", research_job_id: research.id, status: "queued", already_exists: false });
  vi.mocked(getAnalysis).mockRejectedValue(new ApiError("No analysis", 404));
  vi.mocked(retryAnalysis).mockResolvedValue({ analysis_id: "analysis-1", research_job_id: research.id, status: "queued", already_exists: true });
  vi.mocked(getImageMetadata).mockResolvedValue(metadata);
  vi.mocked(getResearch).mockResolvedValue(research);
  vi.mocked(getResearchList).mockResolvedValue({ items: [research], total: 1, limit: 20, offset: 0 });
});

describe("navigation and image selection", () => {
  it("shows the workspace navigation and active page", () => {
    render(<AppShell><p>Dashboard content</p></AppShell>);
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "History" })).toHaveAttribute("href", "/history");
  });

  it("previews a valid image and reports invalid replacement files", () => {
    const onChange = vi.fn();
    const { container } = render(<ImageUploader onChange={onChange} />);
    const input = fileInput(container);
    const validFile = new File([new Uint8Array([1, 2, 3])], "sample.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [validFile] } });
    expect(screen.getByRole("img", { name: "Preview of sample.jpg" })).toBeInTheDocument();
    expect(onChange).toHaveBeenLastCalledWith(validFile);

    const invalidFile = new File(["text"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [invalidFile] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a JPEG, PNG, or WEBP image.");
    expect(screen.queryByRole("img", { name: "Preview of sample.jpg" })).not.toBeInTheDocument();
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("rejects an image above 10 MB", () => {
    const { container } = render(<ImageUploader onChange={vi.fn()} />);
    const tooLarge = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput(container), { target: { files: [tooLarge] } });
    expect(screen.getByRole("alert")).toHaveTextContent("The image must be 10 MB or smaller.");
  });
});

describe("research workflow pages", () => {
  it("uploads through New Research, creates a record, and navigates to its results", async () => {
    const user = userEvent.setup();
    let resolveUpload!: (value: ImageAsset) => void;
    vi.mocked(uploadImage).mockImplementation(() => new Promise((resolve) => { resolveUpload = resolve; }));
    const { container } = render(<NewResearch />);
    const selected = new File([new Uint8Array([1, 2, 3])], "sample.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput(container), { target: { files: [selected] } });
    await user.type(screen.getByLabelText("Subject name, if known"), "Alex Example");
    await user.click(screen.getByRole("button", { name: "Create and queue analysis" }));
    expect(screen.getByRole("status")).toHaveTextContent("Uploading and validating image");
    expect(screen.getByRole("button", { name: "Working…" })).toBeDisabled();
    resolveUpload(image);
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/research/research-1"));
    expect(uploadImage).toHaveBeenCalledWith(selected);
    expect(createResearch).toHaveBeenCalledWith({ image_id: image.id, subject_name: "Alex Example" });
    expect(queueAnalysis).toHaveBeenCalledWith(research.id);
  });

  it("shows upload errors and does not claim success", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadImage).mockRejectedValue(new ApiError("Image exceeds the 10 MB upload limit.", 413));
    const { container } = render(<NewResearch />);
    fireEvent.change(fileInput(container), { target: { files: [new File(["x"], "sample.jpg", { type: "image/jpeg" })] } });
    await user.click(screen.getByRole("button", { name: "Create and queue analysis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Image exceeds the 10 MB upload limit.");
    expect(createResearch).not.toHaveBeenCalled();
  });

  it("loads actual metadata on the forensics page", async () => {
    const user = userEvent.setup();
    const { container } = render(<Forensics />);
    fireEvent.change(fileInput(container), { target: { files: [new File(["x"], "sample.jpg", { type: "image/jpeg" })] } });
    await user.click(screen.getByRole("button", { name: "Inspect image" }));
    expect(await screen.findByText("Sample metadata")).toBeInTheDocument();
    expect(screen.getByText(image.sha256)).toBeInTheDocument();
    expect(getImageMetadata).toHaveBeenCalledWith(image.id);
  });

  it("shows paginated history and navigates to a result", async () => {
    vi.mocked(getResearchList).mockImplementation(async (limit = 20, offset = 0) => ({
      items: offset ? [research] : Array.from({ length: limit }, (_, index) => ({ ...research, id: `research-${index}`, title: `Research ${index}` })),
      total: 21, limit, offset,
    }));
    const user = userEvent.setup();
    render(<History />);
    expect(await screen.findByText("Research 0")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–20 of 21")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open →" })[0]).toHaveAttribute("href", "/research/research-0");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(getResearchList).toHaveBeenLastCalledWith(20, 20));
  });

  it("shows persisted record details and its current workflow state", async () => {
    render(<Results />);
    expect(await screen.findByRole("heading", { name: "Conference image" })).toBeInTheDocument();
    expect(screen.getAllByText("queued").length).toBeGreaterThan(0);
    expect(screen.getByText("Panel speaker")).toBeInTheDocument();
    expect(screen.getByText("No image analysis has been queued for this record.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Uploaded image: sample.jpg" })).toBeInTheDocument();
    expect(getResearch).toHaveBeenCalledWith("research-1");
  });

  it("renders persisted OCR text and aligned bounding-box overlays", async () => {
    vi.mocked(getAnalysis).mockResolvedValue(analysisResult);
    render(<Results />);
    expect(await screen.findByText("hello", { selector: "pre" })).toBeInTheDocument();
    expect(screen.getByText(/Partial results/)).toBeInTheDocument();
    const image = screen.getByRole("img", { name: "Uploaded image: sample.jpg" });
    expect(image).toBeInTheDocument();
    const box = document.querySelector(".ocr-box");
    expect(box).toHaveStyle({ left: "6.25%", top: "12.5%", width: "62.5%", height: "33.33333333333333%" });
  });

  it("uses the backend total for dashboard counts", async () => {
    vi.mocked(getResearchList).mockResolvedValue({ items: [research], total: 61, limit: 5, offset: 0 });
    render(<Dashboard />);
    expect(await screen.findByText("61")).toBeInTheDocument();
    expect(screen.getByText("API available")).toBeInTheDocument();
  });
});

describe("research table states", () => {
  it("shows a useful empty state", () => {
    render(<ResearchTable items={[]} />);
    expect(screen.getByText("No research records yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start new research" })).toHaveAttribute("href", "/research/new");
  });

  it("shows status and a fallback when a thumbnail is unavailable", async () => {
    render(<ResearchTable items={[research]} />);
    expect(screen.getByText("queued")).toBeInTheDocument();
    fireEvent.error(screen.getByRole("img", { name: "Thumbnail for Conference image" }));
    expect(await screen.findByRole("img", { name: "No preview available for Conference image" })).toBeInTheDocument();
  });
});
