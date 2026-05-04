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
  predecessor_id: string | null;
  prop_state: string | null;
  ownership_type: string | null;
  land_ownership: string | null;
  country: string | null;
  region: string | null;
  zip_code: string | null;
  city: string | null;
  street: string | null;
  location_quality: string | null;
  green_building_vendor: string | null;
  green_building_cert: string | null;
  green_building_from: string | null;
  green_building_to: string | null;
  ownership_share: number | null;
  purchase_date: string | null;
  construction_year: number | null;
  risk_style: string | null;
  fair_value: number | null;
  market_net_yield: number | null;
  last_valuation_date: string | null;
  next_valuation_date: string | null;
  plot_size_sqm: number | null;
  debt_property: number | null;
  shareholder_loan: number | null;
  co2_emissions: number | null;
  co2_measurement_year: number | null;
  energy_intensity: number | null;
  energy_intensity_normalised: number | null;
  data_quality_energy: string | null;
  energy_reference_area: number | null;
  crrem_floor_areas_json: Record<string, number> | null;
  exposure_fossil_fuels: number | null;
  exposure_energy_inefficiency: number | null;
  waste_total: number | null;
  waste_recycled_pct: number | null;
  epc_rating: string | null;
  tech_clear_height: number | null;
  tech_floor_load_capacity: number | null;
  tech_loading_docks: number | null;
  tech_sprinkler: string | null;
  tech_lighting: string | null;
  tech_heating: string | null;
  maintenance: string | null;
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

export async function getProperty(id: number): Promise<PropertyMaster> {
  const res = await fetch(`${API_BASE}/api/master-data/properties/${id}`);
  if (!res.ok) throw new Error("Failed to fetch property");
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

// --- Completeness ---

export interface FieldStat {
  filled: number;
  total: number;
  fill_rate: number;
}

export interface FieldGroupStats {
  fields: Record<string, FieldStat>;
}

export interface CompletenessResponse {
  property_groups: Record<string, FieldGroupStats>;
  tenant_fields: Record<string, FieldStat>;
}

export async function getCompleteness(): Promise<CompletenessResponse> {
  const res = await fetch(`${API_BASE}/api/master-data/completeness`);
  if (!res.ok) throw new Error("Failed to fetch completeness");
  return res.json();
}

// --- Fuzzy Match ---

export interface FuzzyMatch {
  id: number;
  name: string;
  score: number;
}

export async function suggestTenants(
  q: string,
  limit = 5
): Promise<FuzzyMatch[]> {
  const sp = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(
    `${API_BASE}/api/master-data/tenants/suggest?${sp.toString()}`
  );
  if (!res.ok) throw new Error("Failed to suggest tenants");
  return res.json();
}

export async function suggestFunds(
  q: string,
  limit = 5
): Promise<FuzzyMatch[]> {
  const sp = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(
    `${API_BASE}/api/master-data/funds/suggest?${sp.toString()}`
  );
  if (!res.ok) throw new Error("Failed to suggest funds");
  return res.json();
}

// --- BVI Import ---

export interface BviImportPreview {
  properties_found: number;
  new_properties: string[];
  existing_properties: string[];
  field_coverage: Record<string, number>;
  bvi_fund_ids: string[];
  warnings: string[];
}

export interface BviImportResult {
  created: number;
  updated: number;
  skipped: number;
  warnings: string[];
}

export async function previewBviImport(
  file: File
): Promise<BviImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/bvi-import/preview`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Preview failed" }));
    throw new Error(err.detail || "Preview failed");
  }
  return res.json();
}

export async function executeBviImport(
  file: File,
  mode: "fill_gaps" | "overwrite" = "fill_gaps"
): Promise<BviImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${API_BASE}/api/bvi-import/execute?mode=${mode}`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Import failed" }));
    throw new Error(err.detail || "Import failed");
  }
  return res.json();
}

// --- Excel Roundtrip ---

export interface ExcelDiff {
  property_id: string;
  field: string;
  current_value: string | null;
  new_value: string;
  change_type: "add" | "update";
}

export interface ExcelPreview {
  diffs: ExcelDiff[];
  total_rows: number;
}

export interface ExcelApplyResult {
  created: number;
  updated: number;
  skipped: number;
}

export function exportPropertiesUrl(): string {
  return `${API_BASE}/api/master-data/properties/export`;
}

export async function previewExcelImport(
  file: File
): Promise<ExcelPreview> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${API_BASE}/api/master-data/properties/import/preview`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Preview failed" }));
    throw new Error(err.detail || "Preview failed");
  }
  return res.json();
}

export async function applyExcelImport(
  file: File,
  mode: "fill_gaps" | "overwrite" = "fill_gaps"
): Promise<ExcelApplyResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${API_BASE}/api/master-data/properties/import/apply?mode=${mode}`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Apply failed" }));
    throw new Error(err.detail || "Apply failed");
  }
  return res.json();
}

// --- Transform / Aggregation ---

export interface Z1Row {
  bvi_fund_id: string | null;
  stichtag: string | null;
  currency: string;
  bvi_tenant_id: string | null;
  property_id: string | null;
  tenant_name: string | null;
  nace_sector: string | null;
  pd_min: number | null;
  pd_max: number | null;
  contractual_rent: number;
}

export interface G2Row {
  fund_id: string | null;
  stichtag: string | null;
  currency: string;
  property_id: string | null;
  label: string | null;
  use_type_primary: string | null;
  country: string | null;
  city: string | null;
  rentable_area: number;
  tenant_count: number;
  floorspace_let: number;
  contractual_rent: number;
  rent_per_sqm: number | null;
  market_rental_value: number;
  reversion: number | null;
  parking_total: number;
  parking_let: number;
  lease_expiry: Record<string, number>;
  lease_term_avg: number | null;
  fair_value: number | null;
  epc_rating: string | null;
  [key: string]: unknown;
}

export interface Z1Preview {
  rows: Z1Row[];
  total: number;
}

export interface G2Preview {
  rows: G2Row[];
  total: number;
}

export interface ValidationIssue {
  property_id: string;
  field: string;
  expected: number;
  actual: number;
  deviation_pct: number;
}

export interface ValidationResult {
  issues: ValidationIssue[];
  total: number;
  properties_checked: number;
}

export async function getZ1Preview(uploadId: number): Promise<Z1Preview> {
  const res = await fetch(
    `${API_BASE}/api/transform/z1/preview?upload_id=${uploadId}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail || "Z1 preview failed");
  }
  return res.json();
}

export async function getG2Preview(uploadId: number): Promise<G2Preview> {
  const res = await fetch(
    `${API_BASE}/api/transform/g2/preview?upload_id=${uploadId}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail || "G2 preview failed");
  }
  return res.json();
}

export async function getValidation(
  uploadId: number
): Promise<ValidationResult> {
  const res = await fetch(
    `${API_BASE}/api/transform/validation?upload_id=${uploadId}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed" }));
    throw new Error(err.detail || "Validation failed");
  }
  return res.json();
}

// --- Periods ---

export interface Period {
  id: number;
  stichtag: string | null;
  upload_id: number | null;
  status: string;
  finalized_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface FinalizeCheck {
  can_finalize: boolean;
  blocking_errors: number;
  unmapped_tenants: number;
  unmapped_funds: number;
  property_completeness_pct: number;
  warnings: string[];
}

export interface FinalizeResult {
  status: string;
  snapshot_counts: Record<string, number>;
}

export async function listPeriods(): Promise<Period[]> {
  const res = await fetch(`${API_BASE}/api/periods`);
  if (!res.ok) throw new Error("Failed to fetch periods");
  return res.json();
}

export async function createPeriod(uploadId: number): Promise<Period> {
  const res = await fetch(`${API_BASE}/api/periods`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id: uploadId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Create failed" }));
    throw new Error(err.detail || "Create failed");
  }
  return res.json();
}

export async function getPeriod(id: number): Promise<Period> {
  const res = await fetch(`${API_BASE}/api/periods/${id}`);
  if (!res.ok) throw new Error("Failed to fetch period");
  return res.json();
}

export async function deletePeriod(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/periods/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Delete failed" }));
    throw new Error(err.detail || "Delete failed");
  }
}

export async function getFinalizeCheck(
  periodId: number
): Promise<FinalizeCheck> {
  const res = await fetch(`${API_BASE}/api/periods/${periodId}/finalize-check`);
  if (!res.ok) throw new Error("Failed to check finalization");
  return res.json();
}

export async function finalizePeriod(
  periodId: number
): Promise<FinalizeResult> {
  const res = await fetch(`${API_BASE}/api/periods/${periodId}/finalize`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Finalize failed" }));
    throw new Error(err.detail || "Finalize failed");
  }
  return res.json();
}

export function periodExportUrl(periodId: number): string {
  return `${API_BASE}/api/periods/${periodId}/export`;
}

// --- Analytics ---

export interface PeriodKPI {
  period_id: number;
  stichtag: string;
  total_rent: number;
  total_area: number;
  vacant_area: number;
  vacancy_rate: number;
  tenant_count: number;
  property_count: number;
  fair_value: number | null;
  total_debt: number | null;
  wault_avg: number | null;
}

export interface PeriodComparisonMetric {
  metric: string;
  period_a_value: number | null;
  period_b_value: number | null;
  delta: number | null;
  delta_pct: number | null;
}

export interface ComparisonResponse {
  period_a: string;
  period_b: string;
  metrics: PeriodComparisonMetric[];
}

export interface PropertySnapshot {
  stichtag: string;
  rent: number;
  area: number;
  vacancy_rate: number;
  tenant_count: number;
  fair_value: number | null;
}

export async function getPortfolioKPIs(
  status: "finalized" | "all" = "finalized"
): Promise<PeriodKPI[]> {
  const res = await fetch(`${API_BASE}/api/analytics/kpis?status=${status}`);
  if (!res.ok) throw new Error("Failed to fetch KPIs");
  return res.json();
}

export async function comparePeriods(
  periodA: number,
  periodB: number
): Promise<ComparisonResponse> {
  const res = await fetch(
    `${API_BASE}/api/analytics/compare?period_a=${periodA}&period_b=${periodB}`
  );
  if (!res.ok) throw new Error("Failed to compare periods");
  return res.json();
}

export async function getPropertyHistory(
  propertyId: string
): Promise<PropertySnapshot[]> {
  const res = await fetch(
    `${API_BASE}/api/analytics/properties/${encodeURIComponent(propertyId)}/history`
  );
  if (!res.ok) throw new Error("Failed to fetch property history");
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

// --- Chat ---

export interface ChatSession {
  id: number;
  title: string | null;
  created_at: string;
  last_message_at: string | null;
}

export interface ChatMessageItem {
  role: string;
  content: string;
  tool_calls: Record<string, unknown>[] | null;
  created_at: string;
}

export interface PendingConfirmation {
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_use_id: string;
  description: string;
}

export interface ChatResponse {
  session_id: number;
  message: string;
  pending_confirmations: PendingConfirmation[];
  tool_results: Record<string, unknown>[];
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/api/chat/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function getChatMessages(
  sessionId: number
): Promise<ChatMessageItem[]> {
  const res = await fetch(
    `${API_BASE}/api/chat/sessions/${sessionId}/messages`
  );
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

export async function deleteChatSession(sessionId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}

export async function sendChatMessage(body: {
  session_id?: number;
  message: string;
  confirmed_tool_calls?: string[];
}): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(err.detail || "Chat failed");
  }
  return res.json();
}

// --- Reports ---

export async function getAvailableFunds(uploadId: number): Promise<string[]> {
  const res = await fetch(
    `${API_BASE}/api/reports/available-funds?upload_id=${uploadId}`
  );
  if (!res.ok) throw new Error("Failed to fetch available funds");
  return res.json();
}

export async function getAvailableProperties(
  uploadId: number
): Promise<string[]> {
  const res = await fetch(
    `${API_BASE}/api/reports/available-properties?upload_id=${uploadId}`
  );
  if (!res.ok) throw new Error("Failed to fetch available properties");
  return res.json();
}

export function getPropertyFactsheetUrl(
  uploadId: number,
  propertyId: string
): string {
  return `${API_BASE}/api/reports/property-factsheet?upload_id=${uploadId}&property_id=${encodeURIComponent(propertyId)}`;
}

export function getPortfolioOverviewUrl(uploadId: number): string {
  return `${API_BASE}/api/reports/portfolio-overview?upload_id=${uploadId}`;
}

export function getLeaseExpiryUrl(uploadId: number): string {
  return `${API_BASE}/api/reports/lease-expiry?upload_id=${uploadId}`;
}

export function getFundSummaryUrl(uploadId: number, fund: string): string {
  return `${API_BASE}/api/reports/fund-summary?upload_id=${uploadId}&fund=${encodeURIComponent(fund)}`;
}

// --- Upload Rows ---

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
