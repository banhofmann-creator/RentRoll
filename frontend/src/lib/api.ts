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

export interface InconsistencyItem {
  id: number;
  upload_id: number;
  category: string;
  severity: string;
  entity_type: string | null;
  entity_id: string | null;
  field_name: string | null;
  expected_value: string | null;
  actual_value: string | null;
  deviation_pct: number | null;
  description: string;
  status: string;
  resolution_note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface InconsistencySummary {
  total: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
  has_blocking_errors: boolean;
}

// --- Master Data Types ---

export interface FundMapping {
  id: number;
  csv_fund_name: string;
  bvi_fund_id: string | null;
  description: string | null;
}

export interface TenantAlias {
  id: number;
  tenant_master_id: number;
  csv_tenant_name: string;
  property_id: string | null;
}

export interface TenantMaster {
  id: number;
  bvi_tenant_id: string | null;
  tenant_name_canonical: string;
  nace_sector: string | null;
  pd_min: number | null;
  pd_max: number | null;
  notes: string | null;
  aliases: TenantAlias[];
}

export interface PropertyMaster {
  id: number;
  property_id: string;
  fund_csv_name: string | null;
  city: string | null;
  street: string | null;
  zip_code: string | null;
  country: string | null;
  region: string | null;
  fair_value: number | null;
  [key: string]: unknown;
}

export interface UnmappedItem {
  entity_type: string;
  entity_id: string;
  upload_count: number;
  inconsistency_ids: number[];
}

// --- Fund Mapping API ---

export async function listFundMappings(params?: {
  search?: string;
  offset?: number;
  limit?: number;
}): Promise<FundMapping[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  const res = await fetch(`${API_BASE}/api/master-data/funds?${sp.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch funds");
  return res.json();
}

export async function createFundMapping(body: {
  csv_fund_name: string;
  bvi_fund_id?: string;
  description?: string;
}): Promise<FundMapping> {
  const res = await fetch(`${API_BASE}/api/master-data/funds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Create failed" }));
    throw new Error(err.detail || "Create failed");
  }
  return res.json();
}

export async function updateFundMapping(
  id: number,
  body: { bvi_fund_id?: string | null; description?: string | null }
): Promise<FundMapping> {
  const res = await fetch(`${API_BASE}/api/master-data/funds/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update fund");
  return res.json();
}

export async function deleteFundMapping(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/master-data/funds/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete fund");
}

// --- Tenant API ---

export async function listTenants(params?: {
  search?: string;
  offset?: number;
  limit?: number;
}): Promise<TenantMaster[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  const res = await fetch(
    `${API_BASE}/api/master-data/tenants?${sp.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch tenants");
  return res.json();
}

export async function createTenant(body: {
  tenant_name_canonical: string;
  bvi_tenant_id?: string;
  nace_sector?: string;
  initial_alias?: string;
}): Promise<TenantMaster> {
  const res = await fetch(`${API_BASE}/api/master-data/tenants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Create failed" }));
    throw new Error(err.detail || "Create failed");
  }
  return res.json();
}

export async function updateTenant(
  id: number,
  body: {
    tenant_name_canonical?: string;
    bvi_tenant_id?: string | null;
    nace_sector?: string | null;
  }
): Promise<TenantMaster> {
  const res = await fetch(`${API_BASE}/api/master-data/tenants/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update tenant");
  return res.json();
}

export async function deleteTenant(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/master-data/tenants/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete tenant");
}

export async function addTenantAlias(
  tenantId: number,
  body: { csv_tenant_name: string; property_id?: string }
): Promise<TenantAlias> {
  const res = await fetch(
    `${API_BASE}/api/master-data/tenants/${tenantId}/aliases`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Add alias failed" }));
    throw new Error(err.detail || "Add alias failed");
  }
  return res.json();
}

export async function removeTenantAlias(
  tenantId: number,
  aliasId: number
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/master-data/tenants/${tenantId}/aliases/${aliasId}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Failed to remove alias");
}

// --- Property API ---

export async function listProperties(params?: {
  search?: string;
  offset?: number;
  limit?: number;
}): Promise<PropertyMaster[]> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  const res = await fetch(
    `${API_BASE}/api/master-data/properties?${sp.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch properties");
  return res.json();
}

export async function createProperty(body: {
  property_id: string;
  fund_csv_name?: string;
  city?: string;
  street?: string;
  country?: string;
  [key: string]: unknown;
}): Promise<PropertyMaster> {
  const res = await fetch(`${API_BASE}/api/master-data/properties`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Create failed" }));
    throw new Error(err.detail || "Create failed");
  }
  return res.json();
}

export async function updateProperty(
  id: number,
  body: Record<string, unknown>
): Promise<PropertyMaster> {
  const res = await fetch(`${API_BASE}/api/master-data/properties/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update property");
  return res.json();
}

export async function deleteProperty(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/master-data/properties/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete property");
}

// --- Unmapped ---

export async function listUnmapped(
  entityType?: string
): Promise<UnmappedItem[]> {
  const sp = entityType ? `?entity_type=${entityType}` : "";
  const res = await fetch(`${API_BASE}/api/master-data/unmapped${sp}`);
  if (!res.ok) throw new Error("Failed to fetch unmapped items");
  return res.json();
}

// --- Inconsistency API ---

export async function listInconsistencies(params?: {
  upload_id?: number;
  category?: string;
  severity?: string;
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<InconsistencyItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.upload_id !== undefined)
    searchParams.set("upload_id", String(params.upload_id));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.offset !== undefined)
    searchParams.set("offset", String(params.offset));
  if (params?.limit !== undefined)
    searchParams.set("limit", String(params.limit));

  const res = await fetch(
    `${API_BASE}/api/inconsistencies?${searchParams.toString()}`
  );
  if (!res.ok) throw new Error("Failed to fetch inconsistencies");
  return res.json();
}

export async function getInconsistencySummary(
  upload_id?: number
): Promise<InconsistencySummary> {
  const params = upload_id !== undefined ? `?upload_id=${upload_id}` : "";
  const res = await fetch(`${API_BASE}/api/inconsistencies/summary${params}`);
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function updateInconsistency(
  id: number,
  body: { status: string; resolution_note?: string; resolved_by?: string }
): Promise<InconsistencyItem> {
  const res = await fetch(`${API_BASE}/api/inconsistencies/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update inconsistency");
  return res.json();
}

export async function recheckInconsistencies(
  uploadId: number
): Promise<{ message: string; count: number }> {
  const res = await fetch(
    `${API_BASE}/api/inconsistencies/${uploadId}/recheck`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Failed to recheck");
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
