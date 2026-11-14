import { afterEach, describe, expect, it, vi } from "vitest";
import { getResearchList, uploadImage } from "@/lib/api/research";

describe("frontend API client contract", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("passes bounded pagination through to the API", async () => {
    const response = { ok: true, json: async () => ({ items: [], total: 53, limit: 20, offset: 40 }) };
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);

    const result = await getResearchList(20, 40);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/research?limit=20&offset=40", undefined);
    expect(result).toEqual({ items: [], total: 53, limit: 20, offset: 40 });
  });

  it("uploads multipart data without overriding its generated boundary", async () => {
    const response = { ok: true, json: async () => ({ id: "image-1" }) };
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["image bytes"], "sample.jpg", { type: "image/jpeg" });

    await uploadImage(file);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toMatchObject({ name: file.name, type: file.type });
    expect(init.headers).toBeUndefined();
  });

  it("normalizes structured API errors without losing the HTTP status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 413,
      json: async () => ({ detail: { code: "file_too_large", message: "Image is too large." } }),
    }));

    await expect(getResearchList()).rejects.toMatchObject({ message: "Image is too large.", status: 413 });
  });
});
