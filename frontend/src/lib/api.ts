const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadResponse {
  id: number;
  filename: string;
  status: string;
  message: string;
}

export interface UploadDetail {
  id: number;
  filename: string;
  upload_date: string;
  stichtag: string | null;
  fund_label: string | null;
  status: string;
  row_count: number | null;
  data_row_count: number | null;
  summary_row_count: number | null;
  orphan_row_count: number | null;
  column_fingerprint: string | null;
  parser_warnings_json: string[] | null;
  error_message: string | null;
}

export interface UploadListItem {
  id: number;
  filename: string;
  upload_date: string;
  stichtag: string | null;
  status: string;
  row_count: number | null;
}

export async function uploadCsv(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function listUploads(): Promise<UploadListItem[]> {
  const res = await fetch(`${API_BASE}/api/uploads`);
  if (!res.ok) throw new Error("Failed to fetch uploads");
  return res.json();
}

export async function getUpload(id: number): Promise<UploadDetail> {
  const res = await fetch(`${API_BASE}/api/uploads/${id}`);
  if (!res.ok) throw new Error("Failed to fetch upload");
  return res.json();
}

export async function getUploadRows(
  id: number,
  params?: {
    row_type?: string;
    fund?: string;
    property_id?: string;
    offset?: number;
    limit?: number;
  }
) {
  const searchParams = new URLSearchParams();
  if (params?.row_type) searchParams.set("row_type", params.row_type);
  if (params?.fund) searchParams.set("fund", params.fund);
  if (params?.property_id) searchParams.set("property_id", params.property_id);
  if (params?.offset !== undefined)
    searchParams.set("offset", String(params.offset));
  if (params?.limit !== undefined)
    searchParams.set("limit", String(params.limit));

  const res = await fetch(
    `${API_BASE}/api/uploads/${id}/rows?${searchParams.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch rows");
  return res.json();
}
