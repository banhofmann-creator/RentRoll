OpenAI Codex v0.123.0 (research preview)
--------
workdir: C:\projects\RentRoll
model: gpt-5.3-codex
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, C:\Users\banho\.codex\memories]
reasoning effort: high
reasoning summaries: none
session id: 019dbf84-1ed6-7930-b3dd-71d957235537
--------
user
current changes
exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'git status --short' in C:\projects\RentRoll
 succeeded in 656ms:
 M CLAUDE.md
 M backend/app/main.py
 M backend/app/models/schemas.py
 M backend/test.db
 M frontend/src/app/globals.css
 M frontend/src/app/layout.tsx
 M frontend/src/lib/api.ts
?? backend/app/api/master_data.py
?? backend/app/core/audit.py
?? backend/tests/test_audit.py
?? backend/tests/test_master_data_api.py
?? frontend/src/app/master-data/
?? planning/reviews/codex-review-20260424-144314.md
warning: unable to access 'C:\Users\banho/.config/git/ignore': Permission denied
warning: unable to access 'C:\Users\banho/.config/git/ignore': Permission denied

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'git diff -- backend/app/main.py backend/app/models/schemas.py frontend/src/lib/api.ts frontend/src/app/layout.tsx frontend/src/app/globals.css CLAUDE.md' in C:\projects\RentRoll
 succeeded in 284ms:
diff --git a/CLAUDE.md b/CLAUDE.md
index eca92f5..e3141b7 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -46,6 +46,18 @@ cd frontend
 npm test
 ```
 
+## Review.md — Mandatory Update
+
+`planning/Review.md` is the execution log. After every non-trivial change (new feature, bug fix, refactor — not typo fixes or config tweaks), update it before considering the work done. Each entry should include:
+- **Status** and **Date**
+- **What was built** — files created/modified, key technical details
+- **Codex review findings** (if review was run) — what was found and how it was fixed
+- **Test coverage** — test count, what's covered
+- **Files changed** — inventory of new and modified files
+- **Deferred items** — anything explicitly left for later
+
+This is as important as the commit itself — it's how future sessions (and other agents) pick up context without re-deriving it from git history.
+
 ## Collaboration Workflow
 
 Use this file as the shared repo contract across coding agents. Keep durable project rules here, and keep task-specific intent in the active prompt.
diff --git a/backend/app/main.py b/backend/app/main.py
index 0d6afbf..055b910 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -5,6 +5,7 @@ from fastapi import FastAPI
 from fastapi.middleware.cors import CORSMiddleware
 
 from app.api.inconsistencies import router as inconsistency_router
+from app.api.master_data import router as master_data_router
 from app.api.upload import router as upload_router
 
 
@@ -33,6 +34,7 @@ app.add_middleware(
 
 app.include_router(upload_router, prefix="/api")
 app.include_router(inconsistency_router, prefix="/api")
+app.include_router(master_data_router, prefix="/api")
 
 
 @app.get("/api/health")
diff --git a/backend/app/models/schemas.py b/backend/app/models/schemas.py
index 556ebc3..1af1d4b 100644
--- a/backend/app/models/schemas.py
+++ b/backend/app/models/schemas.py
@@ -104,3 +104,282 @@ class InconsistencySummary(BaseModel):
     by_category: dict[str, int]
     by_status: dict[str, int]
     has_blocking_errors: bool
+
+
+# --- Fund Mapping ---
+
+class FundMappingCreate(BaseModel):
+    csv_fund_name: str
+    bvi_fund_id: str | None = None
+    description: str | None = None
+
+
+class FundMappingUpdate(BaseModel):
+    bvi_fund_id: str | None = None
+    description: str | None = None
+
+
+class FundMappingResponse(BaseModel):
+    id: int
+    csv_fund_name: str
+    bvi_fund_id: str | None
+    description: str | None
+
+    model_config = {"from_attributes": True}
+
+
+# --- Tenant ---
+
+class TenantAliasCreate(BaseModel):
+    csv_tenant_name: str
+    property_id: str | None = None
+
+
+class TenantAliasResponse(BaseModel):
+    id: int
+    tenant_master_id: int
+    csv_tenant_name: str
+    property_id: str | None
+
+    model_config = {"from_attributes": True}
+
+
+class TenantMasterCreate(BaseModel):
+    tenant_name_canonical: str
+    bvi_tenant_id: str | None = None
+    nace_sector: str | None = None
+    pd_min: float | None = None
+    pd_max: float | None = None
+    notes: str | None = None
+    initial_alias: str | None = None
+
+
+class TenantMasterUpdate(BaseModel):
+    tenant_name_canonical: str | None = None
+    bvi_tenant_id: str | None = None
+    nace_sector: str | None = None
+    pd_min: float | None = None
+    pd_max: float | None = None
+    notes: str | None = None
+
+
+class TenantMasterResponse(BaseModel):
+    id: int
+    bvi_tenant_id: str | None
+    tenant_name_canonical: str
+    nace_sector: str | None
+    pd_min: float | None
+    pd_max: float | None
+    notes: str | None
+    aliases: list[TenantAliasResponse]
+
+    model_config = {"from_attributes": True}
+
+
+# --- Property Master ---
+
+_PROPERTY_OPTIONAL_FIELDS = dict(
+    fund_csv_name=(str | None, None),
+    predecessor_id=(str | None, None),
+    prop_state=(str | None, None),
+    ownership_type=(str | None, None),
+    land_ownership=(str | None, None),
+    country=(str | None, None),
+    region=(str | None, None),
+    zip_code=(str | None, None),
+    city=(str | None, None),
+    street=(str | None, None),
+    location_quality=(str | None, None),
+    green_building_vendor=(str | None, None),
+    green_building_cert=(str | None, None),
+    green_building_from=(date | None, None),
+    green_building_to=(date | None, None),
+    ownership_share=(float | None, None),
+    purchase_date=(date | None, None),
+    construction_year=(int | None, None),
+    risk_style=(str | None, None),
+    fair_value=(float | None, None),
+    market_net_yield=(float | None, None),
+    last_valuation_date=(date | None, None),
+    next_valuation_date=(date | None, None),
+    plot_size_sqm=(float | None, None),
+    debt_property=(float | None, None),
+    shareholder_loan=(float | None, None),
+    co2_emissions=(float | None, None),
+    co2_measurement_year=(int | None, None),
+    energy_intensity=(float | None, None),
+    energy_intensity_normalised=(float | None, None),
+    data_quality_energy=(str | None, None),
+    energy_reference_area=(float | None, None),
+    crrem_floor_areas_json=(dict | None, None),
+    exposure_fossil_fuels=(float | None, None),
+    exposure_energy_inefficiency=(float | None, None),
+    waste_total=(float | None, None),
+    waste_recycled_pct=(float | None, None),
+    epc_rating=(str | None, None),
+    tech_clear_height=(float | None, None),
+    tech_floor_load_capacity=(float | None, None),
+    tech_loading_docks=(int | None, None),
+    tech_sprinkler=(str | None, None),
+    tech_lighting=(str | None, None),
+    tech_heating=(str | None, None),
+    maintenance=(str | None, None),
+)
+
+
+class PropertyMasterCreate(BaseModel):
+    property_id: str
+    fund_csv_name: str | None = None
+    predecessor_id: str | None = None
+    prop_state: str | None = None
+    ownership_type: str | None = None
+    land_ownership: str | None = None
+    country: str | None = None
+    region: str | None = None
+    zip_code: str | None = None
+    city: str | None = None
+    street: str | None = None
+    location_quality: str | None = None
+    green_building_vendor: str | None = None
+    green_building_cert: str | None = None
+    green_building_from: date | None = None
+    green_building_to: date | None = None
+    ownership_share: float | None = None
+    purchase_date: date | None = None
+    construction_year: int | None = None
+    risk_style: str | None = None
+    fair_value: float | None = None
+    market_net_yield: float | None = None
+    last_valuation_date: date | None = None
+    next_valuation_date: date | None = None
+    plot_size_sqm: float | None = None
+    debt_property: float | None = None
+    shareholder_loan: float | None = None
+    co2_emissions: float | None = None
+    co2_measurement_year: int | None = None
+    energy_intensity: float | None = None
+    energy_intensity_normalised: float | None = None
+    data_quality_energy: str | None = None
+    energy_reference_area: float | None = None
+    crrem_floor_areas_json: dict | None = None
+    exposure_fossil_fuels: float | None = None
+    exposure_energy_inefficiency: float | None = None
+    waste_total: float | None = None
+    waste_recycled_pct: float | None = None
+    epc_rating: str | None = None
+    tech_clear_height: float | None = None
+    tech_floor_load_capacity: float | None = None
+    tech_loading_docks: int | None = None
+    tech_sprinkler: str | None = None
+    tech_lighting: str | None = None
+    tech_heating: str | None = None
+    maintenance: str | None = None
+
+
+class PropertyMasterUpdate(BaseModel):
+    fund_csv_name: str | None = None
+    predecessor_id: str | None = None
+    prop_state: str | None = None
+    ownership_type: str | None = None
+    land_ownership: str | None = None
+    country: str | None = None
+    region: str | None = None
+    zip_code: str | None = None
+    city: str | None = None
+    street: str | None = None
+    location_quality: str | None = None
+    green_building_vendor: str | None = None
+    green_building_cert: str | None = None
+    green_building_from: date | None = None
+    green_building_to: date | None = None
+    ownership_share: float | None = None
+    purchase_date: date | None = None
+    construction_year: int | None = None
+    risk_style: str | None = None
+    fair_value: float | None = None
+    market_net_yield: float | None = None
+    last_valuation_date: date | None = None
+    next_valuation_date: date | None = None
+    plot_size_sqm: float | None = None
+    debt_property: float | None = None
+    shareholder_loan: float | None = None
+    co2_emissions: float | None = None
+    co2_measurement_year: int | None = None
+    energy_intensity: float | None = None
+    energy_intensity_normalised: float | None = None
+    data_quality_energy: str | None = None
+    energy_reference_area: float | None = None
+    crrem_floor_areas_json: dict | None = None
+    exposure_fossil_fuels: float | None = None
+    exposure_energy_inefficiency: float | None = None
+    waste_total: float | None = None
+    waste_recycled_pct: float | None = None
+    epc_rating: str | None = None
+    tech_clear_height: float | None = None
+    tech_floor_load_capacity: float | None = None
+    tech_loading_docks: int | None = None
+    tech_sprinkler: str | None = None
+    tech_lighting: str | None = None
+    tech_heating: str | None = None
+    maintenance: str | None = None
+
+
+class PropertyMasterResponse(BaseModel):
+    id: int
+    property_id: str
+    fund_csv_name: str | None
+    predecessor_id: str | None
+    prop_state: str | None
+    ownership_type: str | None
+    land_ownership: str | None
+    country: str | None
+    region: str | None
+    zip_code: str | None
+    city: str | None
+    street: str | None
+    location_quality: str | None
+    green_building_vendor: str | None
+    green_building_cert: str | None
+    green_building_from: date | None
+    green_building_to: date | None
+    ownership_share: float | None
+    purchase_date: date | None
+    construction_year: int | None
+    risk_style: str | None
+    fair_value: float | None
+    market_net_yield: float | None
+    last_valuation_date: date | None
+    next_valuation_date: date | None
+    plot_size_sqm: float | None
+    debt_property: float | None
+    shareholder_loan: float | None
+    co2_emissions: float | None
+    co2_measurement_year: int | None
+    energy_intensity: float | None
+    energy_intensity_normalised: float | None
+    data_quality_energy: str | None
+    energy_reference_area: float | None
+    crrem_floor_areas_json: dict | None
+    exposure_fossil_fuels: float | None
+    exposure_energy_inefficiency: float | None
+    waste_total: float | None
+    waste_recycled_pct: float | None
+    epc_rating: str | None
+    tech_clear_height: float | None
+    tech_floor_load_capacity: float | None
+    tech_loading_docks: int | None
+    tech_sprinkler: str | None
+    tech_lighting: str | None
+    tech_heating: str | None
+    maintenance: str | None
+
+    model_config = {"from_attributes": True}
+
+
+# --- Unmapped Items ---
+
+class UnmappedItem(BaseModel):
+    entity_type: str
+    entity_id: str
+    upload_count: int
+    inconsistency_ids: list[int]
diff --git a/frontend/src/app/globals.css b/frontend/src/app/globals.css
index a1070dd..e8c5444 100644
--- a/frontend/src/app/globals.css
+++ b/frontend/src/app/globals.css
@@ -39,3 +39,17 @@ h3, h4 {
   letter-spacing: 0.045em;
   color: var(--color-garbe-blau);
 }
+
+.form-input {
+  border: 1px solid var(--color-garbe-neutral);
+  border-radius: 0.5rem;
+  padding: 0.5rem 0.75rem;
+  font-size: 0.875rem;
+  background: white;
+  color: var(--color-garbe-blau);
+}
+
+.form-input:focus {
+  border-color: var(--color-garbe-blau-60);
+  outline: none;
+}
diff --git a/frontend/src/app/layout.tsx b/frontend/src/app/layout.tsx
index d992e8a..b0d9586 100644
--- a/frontend/src/app/layout.tsx
+++ b/frontend/src/app/layout.tsx
@@ -49,6 +49,12 @@ export default function RootLayout({
                 >
                   Quality
                 </Link>
+                <Link
+                  href="/master-data"
+                  className="text-garbe-blau-20 hover:text-white transition-colors"
+                >
+                  Master Data
+                </Link>
               </div>
             </div>
           </div>
diff --git a/frontend/src/lib/api.ts b/frontend/src/lib/api.ts
index 2efad6d..7ff9aa8 100644
--- a/frontend/src/lib/api.ts
+++ b/frontend/src/lib/api.ts
@@ -88,6 +88,267 @@ export interface InconsistencySummary {
   has_blocking_errors: boolean;
 }
 
+// --- Master Data Types ---
+
+export interface FundMapping {
+  id: number;
+  csv_fund_name: string;
+  bvi_fund_id: string | null;
+  description: string | null;
+}
+
+export interface TenantAlias {
+  id: number;
+  tenant_master_id: number;
+  csv_tenant_name: string;
+  property_id: string | null;
+}
+
+export interface TenantMaster {
+  id: number;
+  bvi_tenant_id: string | null;
+  tenant_name_canonical: string;
+  nace_sector: string | null;
+  pd_min: number | null;
+  pd_max: number | null;
+  notes: string | null;
+  aliases: TenantAlias[];
+}
+
+export interface PropertyMaster {
+  id: number;
+  property_id: string;
+  fund_csv_name: string | null;
+  city: string | null;
+  street: string | null;
+  zip_code: string | null;
+  country: string | null;
+  region: string | null;
+  fair_value: number | null;
+  [key: string]: unknown;
+}
+
+export interface UnmappedItem {
+  entity_type: string;
+  entity_id: string;
+  upload_count: number;
+  inconsistency_ids: number[];
+}
+
+// --- Fund Mapping API ---
+
+export async function listFundMappings(params?: {
+  search?: string;
+  offset?: number;
+  limit?: number;
+}): Promise<FundMapping[]> {
+  const sp = new URLSearchParams();
+  if (params?.search) sp.set("search", params.search);
+  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
+  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
+  const res = await fetch(`${API_BASE}/api/master-data/funds?${sp.toString()}`);
+  if (!res.ok) throw new Error("Failed to fetch funds");
+  return res.json();
+}
+
+export async function createFundMapping(body: {
+  csv_fund_name: string;
+  bvi_fund_id?: string;
+  description?: string;
+}): Promise<FundMapping> {
+  const res = await fetch(`${API_BASE}/api/master-data/funds`, {
+    method: "POST",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) {
+    const err = await res.json().catch(() => ({ detail: "Create failed" }));
+    throw new Error(err.detail || "Create failed");
+  }
+  return res.json();
+}
+
+export async function updateFundMapping(
+  id: number,
+  body: { bvi_fund_id?: string; description?: string }
+): Promise<FundMapping> {
+  const res = await fetch(`${API_BASE}/api/master-data/funds/${id}`, {
+    method: "PATCH",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) throw new Error("Failed to update fund");
+  return res.json();
+}
+
+export async function deleteFundMapping(id: number): Promise<void> {
+  const res = await fetch(`${API_BASE}/api/master-data/funds/${id}`, {
+    method: "DELETE",
+  });
+  if (!res.ok) throw new Error("Failed to delete fund");
+}
+
+// --- Tenant API ---
+
+export async function listTenants(params?: {
+  search?: string;
+  offset?: number;
+  limit?: number;
+}): Promise<TenantMaster[]> {
+  const sp = new URLSearchParams();
+  if (params?.search) sp.set("search", params.search);
+  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
+  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
+  const res = await fetch(
+    `${API_BASE}/api/master-data/tenants?${sp.toString()}`
+  );
+  if (!res.ok) throw new Error("Failed to fetch tenants");
+  return res.json();
+}
+
+export async function createTenant(body: {
+  tenant_name_canonical: string;
+  bvi_tenant_id?: string;
+  nace_sector?: string;
+  initial_alias?: string;
+}): Promise<TenantMaster> {
+  const res = await fetch(`${API_BASE}/api/master-data/tenants`, {
+    method: "POST",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) {
+    const err = await res.json().catch(() => ({ detail: "Create failed" }));
+    throw new Error(err.detail || "Create failed");
+  }
+  return res.json();
+}
+
+export async function updateTenant(
+  id: number,
+  body: {
+    tenant_name_canonical?: string;
+    bvi_tenant_id?: string;
+    nace_sector?: string;
+  }
+): Promise<TenantMaster> {
+  const res = await fetch(`${API_BASE}/api/master-data/tenants/${id}`, {
+    method: "PATCH",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) throw new Error("Failed to update tenant");
+  return res.json();
+}
+
+export async function deleteTenant(id: number): Promise<void> {
+  const res = await fetch(`${API_BASE}/api/master-data/tenants/${id}`, {
+    method: "DELETE",
+  });
+  if (!res.ok) throw new Error("Failed to delete tenant");
+}
+
+export async function addTenantAlias(
+  tenantId: number,
+  body: { csv_tenant_name: string; property_id?: string }
+): Promise<TenantAlias> {
+  const res = await fetch(
+    `${API_BASE}/api/master-data/tenants/${tenantId}/aliases`,
+    {
+      method: "POST",
+      headers: { "Content-Type": "application/json" },
+      body: JSON.stringify(body),
+    }
+  );
+  if (!res.ok) {
+    const err = await res.json().catch(() => ({ detail: "Add alias failed" }));
+    throw new Error(err.detail || "Add alias failed");
+  }
+  return res.json();
+}
+
+export async function removeTenantAlias(
+  tenantId: number,
+  aliasId: number
+): Promise<void> {
+  const res = await fetch(
+    `${API_BASE}/api/master-data/tenants/${tenantId}/aliases/${aliasId}`,
+    { method: "DELETE" }
+  );
+  if (!res.ok) throw new Error("Failed to remove alias");
+}
+
+// --- Property API ---
+
+export async function listProperties(params?: {
+  search?: string;
+  offset?: number;
+  limit?: number;
+}): Promise<PropertyMaster[]> {
+  const sp = new URLSearchParams();
+  if (params?.search) sp.set("search", params.search);
+  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
+  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
+  const res = await fetch(
+    `${API_BASE}/api/master-data/properties?${sp.toString()}`
+  );
+  if (!res.ok) throw new Error("Failed to fetch properties");
+  return res.json();
+}
+
+export async function createProperty(body: {
+  property_id: string;
+  fund_csv_name?: string;
+  city?: string;
+  street?: string;
+  country?: string;
+  [key: string]: unknown;
+}): Promise<PropertyMaster> {
+  const res = await fetch(`${API_BASE}/api/master-data/properties`, {
+    method: "POST",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) {
+    const err = await res.json().catch(() => ({ detail: "Create failed" }));
+    throw new Error(err.detail || "Create failed");
+  }
+  return res.json();
+}
+
+export async function updateProperty(
+  id: number,
+  body: Record<string, unknown>
+): Promise<PropertyMaster> {
+  const res = await fetch(`${API_BASE}/api/master-data/properties/${id}`, {
+    method: "PATCH",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+  if (!res.ok) throw new Error("Failed to update property");
+  return res.json();
+}
+
+export async function deleteProperty(id: number): Promise<void> {
+  const res = await fetch(`${API_BASE}/api/master-data/properties/${id}`, {
+    method: "DELETE",
+  });
+  if (!res.ok) throw new Error("Failed to delete property");
+}
+
+// --- Unmapped ---
+
+export async function listUnmapped(
+  entityType?: string
+): Promise<UnmappedItem[]> {
+  const sp = entityType ? `?entity_type=${entityType}` : "";
+  const res = await fetch(`${API_BASE}/api/master-data/unmapped${sp}`);
+  if (!res.ok) throw new Error("Failed to fetch unmapped items");
+  return res.json();
+}
+
+// --- Inconsistency API ---
+
 export async function listInconsistencies(params?: {
   upload_id?: number;
   category?: string;
warning: in the working copy of 'CLAUDE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/app/main.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/app/models/schemas.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/app/globals.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/app/layout.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/lib/api.ts', LF will be replaced by CRLF the next time Git touches it

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'git diff --cached --name-only' in C:\projects\RentRoll
 succeeded in 266ms:
warning: unable to access 'C:\Users\banho/.config/git/ignore': Permission denied

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem -Recurse frontend/src/app/master-data | Select-Object FullName' in C:\projects\RentRoll
 succeeded in 372ms:

FullName                                                  
--------                                                  
C:\projects\RentRoll\frontend\src\app\master-data\page.tsx



exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/api/master_data.py' in C:\projects\RentRoll
 succeeded in 321ms:
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_changes, log_creation, log_deletion, snapshot
from app.database import get_db
from app.models.database import (
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    TenantMaster,
    TenantNameAlias,
)
from app.models.schemas import (
    FundMappingCreate,
    FundMappingResponse,
    FundMappingUpdate,
    PropertyMasterCreate,
    PropertyMasterResponse,
    PropertyMasterUpdate,
    TenantAliasCreate,
    TenantAliasResponse,
    TenantMasterCreate,
    TenantMasterResponse,
    TenantMasterUpdate,
    UnmappedItem,
)

router = APIRouter(tags=["master-data"])

FUND_FIELDS = ["csv_fund_name", "bvi_fund_id", "description"]
TENANT_FIELDS = [
    "tenant_name_canonical", "bvi_tenant_id", "nace_sector",
    "pd_min", "pd_max", "notes",
]
PROPERTY_FIELDS = [
    "property_id", "fund_csv_name", "predecessor_id", "prop_state",
    "ownership_type", "land_ownership", "country", "region", "zip_code",
    "city", "street", "location_quality", "green_building_vendor",
    "green_building_cert", "green_building_from", "green_building_to",
    "ownership_share", "purchase_date", "construction_year", "risk_style",
    "fair_value", "market_net_yield", "last_valuation_date",
    "next_valuation_date", "plot_size_sqm", "debt_property",
    "shareholder_loan", "co2_emissions", "co2_measurement_year",
    "energy_intensity", "energy_intensity_normalised", "data_quality_energy",
    "energy_reference_area", "crrem_floor_areas_json",
    "exposure_fossil_fuels", "exposure_energy_inefficiency", "waste_total",
    "waste_recycled_pct", "epc_rating", "tech_clear_height",
    "tech_floor_load_capacity", "tech_loading_docks", "tech_sprinkler",
    "tech_lighting", "tech_heating", "maintenance",
]


# â”€â”€ Auto-resolution helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _resolve_inconsistencies(db: Session, category: str, entity_id: str):
    db.query(DataInconsistency).filter(
        DataInconsistency.category == category,
        DataInconsistency.entity_id == entity_id,
        DataInconsistency.status == "open",
    ).update(
        {
            "status": "resolved",
            "resolution_note": "Auto-resolved: mapping created",
            "resolved_at": datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )


# â”€â”€ Fund Mapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/master-data/funds", response_model=list[FundMappingResponse])
def list_funds(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(FundMapping)
    if search:
        query = query.filter(FundMapping.csv_fund_name.ilike(f"%{search}%"))
    return query.order_by(FundMapping.csv_fund_name).offset(offset).limit(limit).all()


@router.post("/master-data/funds", response_model=FundMappingResponse)
def create_fund(body: FundMappingCreate, db: Session = Depends(get_db)):
    existing = db.query(FundMapping).filter(
        FundMapping.csv_fund_name == body.csv_fund_name
    ).first()
    if existing:
        raise HTTPException(400, f"Fund mapping for '{body.csv_fund_name}' already exists")

    fund = FundMapping(**body.model_dump())
    db.add(fund)
    db.flush()
    log_creation(db, "fund_mapping", fund.id, snapshot(fund, FUND_FIELDS))
    _resolve_inconsistencies(db, "unmapped_fund", body.csv_fund_name)
    db.commit()
    db.refresh(fund)
    return fund


@router.patch("/master-data/funds/{fund_id}", response_model=FundMappingResponse)
def update_fund(fund_id: int, body: FundMappingUpdate, db: Session = Depends(get_db)):
    fund = db.get(FundMapping, fund_id)
    if not fund:
        raise HTTPException(404, "Fund mapping not found")

    old = snapshot(fund, FUND_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(fund, field, val)
    log_changes(db, "fund_mapping", fund.id, old, updates)
    db.commit()
    db.refresh(fund)
    return fund


@router.delete("/master-data/funds/{fund_id}")
def delete_fund(fund_id: int, db: Session = Depends(get_db)):
    fund = db.get(FundMapping, fund_id)
    if not fund:
        raise HTTPException(404, "Fund mapping not found")
    log_deletion(db, "fund_mapping", fund.id, snapshot(fund, FUND_FIELDS))
    db.delete(fund)
    db.commit()
    return {"message": "Fund mapping deleted"}


# â”€â”€ Tenant Master â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/master-data/tenants", response_model=list[TenantMasterResponse])
def list_tenants(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(TenantMaster).options(selectinload(TenantMaster.aliases))
    if search:
        query = (
            query.outerjoin(TenantNameAlias)
            .filter(or_(
                TenantMaster.tenant_name_canonical.ilike(f"%{search}%"),
                TenantNameAlias.csv_tenant_name.ilike(f"%{search}%"),
            ))
            .distinct()
        )
    return (
        query.order_by(TenantMaster.tenant_name_canonical)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/master-data/tenants", response_model=TenantMasterResponse)
def create_tenant(body: TenantMasterCreate, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"initial_alias"})
    tenant = TenantMaster(**data)
    db.add(tenant)
    db.flush()
    log_creation(db, "tenant_master", tenant.id, snapshot(tenant, TENANT_FIELDS))

    if body.initial_alias:
        alias = TenantNameAlias(
            tenant_master_id=tenant.id,
            csv_tenant_name=body.initial_alias,
        )
        db.add(alias)
        _resolve_inconsistencies(db, "unmapped_tenant", body.initial_alias)

    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = (
        db.query(TenantMaster)
        .options(selectinload(TenantMaster.aliases))
        .filter(TenantMaster.id == tenant_id)
        .first()
    )
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.patch("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
def update_tenant(tenant_id: int, body: TenantMasterUpdate, db: Session = Depends(get_db)):
    tenant = db.get(TenantMaster, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    old = snapshot(tenant, TENANT_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(tenant, field, val)
    log_changes(db, "tenant_master", tenant.id, old, updates)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/master-data/tenants/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = (
        db.query(TenantMaster)
        .options(selectinload(TenantMaster.aliases))
        .filter(TenantMaster.id == tenant_id)
        .first()
    )
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    log_deletion(db, "tenant_master", tenant.id, snapshot(tenant, TENANT_FIELDS))
    db.delete(tenant)
    db.commit()
    return {"message": "Tenant deleted"}


# â”€â”€ Tenant Aliases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post(
    "/master-data/tenants/{tenant_id}/aliases",
    response_model=TenantAliasResponse,
)
def add_alias(tenant_id: int, body: TenantAliasCreate, db: Session = Depends(get_db)):
    tenant = db.get(TenantMaster, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    existing = db.query(TenantNameAlias).filter(
        TenantNameAlias.csv_tenant_name == body.csv_tenant_name
    ).first()
    if existing:
        raise HTTPException(400, f"Alias '{body.csv_tenant_name}' already exists")

    alias = TenantNameAlias(
        tenant_master_id=tenant_id,
        csv_tenant_name=body.csv_tenant_name,
        property_id=body.property_id,
    )
    db.add(alias)
    db.flush()
    _resolve_inconsistencies(db, "unmapped_tenant", body.csv_tenant_name)
    db.commit()
    db.refresh(alias)
    return alias


@router.delete("/master-data/tenants/{tenant_id}/aliases/{alias_id}")
def remove_alias(tenant_id: int, alias_id: int, db: Session = Depends(get_db)):
    alias = db.query(TenantNameAlias).filter(
        TenantNameAlias.id == alias_id,
        TenantNameAlias.tenant_master_id == tenant_id,
    ).first()
    if not alias:
        raise HTTPException(404, "Alias not found")
    log_deletion(
        db, "tenant_name_alias", alias.id,
        {"csv_tenant_name": alias.csv_tenant_name, "property_id": alias.property_id},
    )
    db.delete(alias)
    db.commit()
    return {"message": "Alias removed"}


# â”€â”€ Property Master â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/master-data/properties", response_model=list[PropertyMasterResponse])
def list_properties(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(PropertyMaster)
    if search:
        query = query.filter(or_(
            PropertyMaster.property_id.ilike(f"%{search}%"),
            PropertyMaster.city.ilike(f"%{search}%"),
        ))
    return query.order_by(PropertyMaster.property_id).offset(offset).limit(limit).all()


@router.post("/master-data/properties", response_model=PropertyMasterResponse)
def create_property(body: PropertyMasterCreate, db: Session = Depends(get_db)):
    existing = db.query(PropertyMaster).filter(
        PropertyMaster.property_id == body.property_id
    ).first()
    if existing:
        raise HTTPException(400, f"Property '{body.property_id}' already exists")

    prop = PropertyMaster(**body.model_dump())
    db.add(prop)
    db.flush()
    log_creation(db, "property_master", prop.id, snapshot(prop, PROPERTY_FIELDS))
    _resolve_inconsistencies(db, "missing_metadata", body.property_id)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/master-data/properties/{property_id}", response_model=PropertyMasterResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    return prop


@router.patch("/master-data/properties/{property_id}", response_model=PropertyMasterResponse)
def update_property(property_id: int, body: PropertyMasterUpdate, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")

    old = snapshot(prop, PROPERTY_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(prop, field, val)
    log_changes(db, "property_master", prop.id, old, updates)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/master-data/properties/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    log_deletion(db, "property_master", prop.id, snapshot(prop, PROPERTY_FIELDS))
    db.delete(prop)
    db.commit()
    return {"message": "Property deleted"}


# â”€â”€ Unmapped Items â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CATEGORY_TO_ENTITY = {
    "unmapped_fund": "fund",
    "unmapped_tenant": "tenant",
    "missing_metadata": "property",
}


@router.get("/master-data/unmapped", response_model=list[UnmappedItem])
def list_unmapped(
    entity_type: str | None = None,
    db: Session = Depends(get_db),
):
    categories = list(CATEGORY_TO_ENTITY.keys())
    if entity_type:
        categories = [c for c, e in CATEGORY_TO_ENTITY.items() if e == entity_type]

    rows = (
        db.query(DataInconsistency)
        .filter(
            DataInconsistency.category.in_(categories),
            DataInconsistency.status == "open",
        )
        .all()
    )

    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    upload_counts: dict[tuple[str, str], set[int]] = defaultdict(set)

    for r in rows:
        etype = CATEGORY_TO_ENTITY.get(r.category, r.category)
        key = (etype, r.entity_id or "")
        grouped[key].append(r.id)
        upload_counts[key].add(r.upload_id)

    return [
        UnmappedItem(
            entity_type=etype,
            entity_id=eid,
            upload_count=len(upload_counts[(etype, eid)]),
            inconsistency_ids=ids,
        )
        for (etype, eid), ids in sorted(grouped.items())
    ]

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/core/audit.py' in C:\projects\RentRoll
 succeeded in 286ms:
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.database import MasterDataAudit


def _serialize(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def snapshot(obj, fields: list[str]) -> dict:
    return {f: getattr(obj, f, None) for f in fields}


def log_changes(
    db: Session,
    table_name: str,
    record_id: int,
    old_values: dict,
    new_values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, new_val in new_values.items():
        old_val = old_values.get(field)
        if _serialize(old_val) != _serialize(new_val):
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=_serialize(old_val),
                new_value=_serialize(new_val),
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries


def log_creation(
    db: Session,
    table_name: str,
    record_id: int,
    values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, val in values.items():
        if val is not None:
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=None,
                new_value=_serialize(val),
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries


def log_deletion(
    db: Session,
    table_name: str,
    record_id: int,
    values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, val in values.items():
        if val is not None:
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=_serialize(val),
                new_value=None,
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/tests/test_audit.py' in C:\projects\RentRoll
 succeeded in 294ms:
import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.database import MasterDataAudit
from app.core.audit import log_changes, log_creation, log_deletion, snapshot

test_engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


def test_log_changes_detects_diffs(db):
    old = {"name": "Old Name", "value": "100"}
    new = {"name": "New Name", "value": "200"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    assert len(entries) == 2
    names = {e.field_name for e in entries}
    assert names == {"name", "value"}
    for e in entries:
        assert e.table_name == "test_table"
        assert e.record_id == 1


def test_log_changes_ignores_unchanged(db):
    old = {"name": "Same", "value": "100"}
    new = {"name": "Same", "value": "200"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    assert len(entries) == 1
    assert entries[0].field_name == "value"


def test_log_changes_handles_types(db):
    old = {"d": date(2025, 1, 1), "n": Decimal("10.50"), "x": None}
    new = {"d": date(2025, 6, 1), "n": Decimal("20.00"), "x": "now set"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    by_field = {e.field_name: e for e in entries}
    assert by_field["d"].old_value == "2025-01-01"
    assert by_field["d"].new_value == "2025-06-01"
    assert by_field["n"].old_value == "10.50"
    assert by_field["n"].new_value == "20.00"
    assert by_field["x"].old_value is None
    assert by_field["x"].new_value == "now set"


def test_log_creation_records_non_none(db):
    values = {"name": "Test", "count": 5, "empty": None}
    entries = log_creation(db, "test_table", 1, values)
    db.commit()

    assert len(entries) == 2
    for e in entries:
        assert e.old_value is None
        assert e.new_value is not None


def test_log_deletion_records_non_none(db):
    values = {"name": "Test", "count": 5, "empty": None}
    entries = log_deletion(db, "test_table", 1, values)
    db.commit()

    assert len(entries) == 2
    for e in entries:
        assert e.old_value is not None
        assert e.new_value is None


def test_snapshot_captures_fields():
    class FakeObj:
        a = "hello"
        b = 42
        c = None

    result = snapshot(FakeObj(), ["a", "b", "c"])
    assert result == {"a": "hello", "b": 42, "c": None}

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/tests/test_master_data_api.py' in C:\projects\RentRoll
 succeeded in 295ms:
import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.models.database import (
    CsvUpload,
    DataInconsistency,
    FundMapping,
    MasterDataAudit,
    PropertyMaster,
    TenantMaster,
    TenantNameAlias,
)

test_engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(test_engine)

    from app.api.upload import set_session_factory
    set_session_factory(TestSession)
    yield
    set_session_factory(None)
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client():
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


# â”€â”€ Fund Mapping Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_create_fund(client):
    resp = client.post("/api/master-data/funds", json={
        "csv_fund_name": "GLIF",
        "bvi_fund_id": "F01",
        "description": "Test fund",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["csv_fund_name"] == "GLIF"
    assert data["bvi_fund_id"] == "F01"


def test_create_fund_duplicate(client):
    client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    assert resp.status_code == 400


def test_list_funds(client):
    for name in ["GLIF", "GLIFPLUSII", "OTHER"]:
        client.post("/api/master-data/funds", json={"csv_fund_name": name})
    resp = client.get("/api/master-data/funds")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_funds_search(client):
    for name in ["GLIF", "GLIFPLUSII", "OTHER"]:
        client.post("/api/master-data/funds", json={"csv_fund_name": name})
    resp = client.get("/api/master-data/funds?search=GLIF")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all("GLIF" in f["csv_fund_name"] for f in data)


def test_update_fund(client):
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    fund_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/funds/{fund_id}", json={
        "bvi_fund_id": "F99",
        "description": "Updated",
    })
    assert resp.status_code == 200
    assert resp.json()["bvi_fund_id"] == "F99"
    assert resp.json()["description"] == "Updated"


def test_update_fund_not_found(client):
    resp = client.patch("/api/master-data/funds/99999", json={"bvi_fund_id": "X"})
    assert resp.status_code == 404


def test_delete_fund(client):
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    fund_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/funds/{fund_id}")
    assert resp.status_code == 200

    resp = client.get("/api/master-data/funds")
    assert len(resp.json()) == 0


def test_create_fund_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="unmapped_fund",
        severity="error",
        entity_type="fund",
        entity_id="TESTFUND",
        description="Fund 'TESTFUND' has no mapping",
        status="open",
    ))
    db.commit()

    client.post("/api/master-data/funds", json={"csv_fund_name": "TESTFUND"})

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "TESTFUND"
    ).first()
    assert inc.status == "resolved"


# â”€â”€ Tenant Master Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_create_tenant(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme Corp",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_name_canonical"] == "Acme Corp"
    assert data["aliases"] == []


def test_create_tenant_with_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme Corp",
        "initial_alias": "ACME CORP GMBH",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["aliases"]) == 1
    assert data["aliases"][0]["csv_tenant_name"] == "ACME CORP GMBH"


def test_list_tenants(client):
    for name in ["Alpha", "Beta", "Gamma"]:
        client.post("/api/master-data/tenants", json={"tenant_name_canonical": name})
    resp = client.get("/api/master-data/tenants")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_tenants_search_canonical(client):
    for name in ["Alpha Corp", "Beta Inc", "Gamma Ltd"]:
        client.post("/api/master-data/tenants", json={"tenant_name_canonical": name})
    resp = client.get("/api/master-data/tenants?search=Alpha")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_tenants_search_by_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Alpha Corp",
        "initial_alias": "ALPHA GMBH",
    })
    client.post("/api/master-data/tenants", json={"tenant_name_canonical": "Beta Inc"})

    resp = client.get("/api/master-data/tenants?search=ALPHA GMBH")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tenant_name_canonical"] == "Alpha Corp"


def test_get_tenant_detail(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.get(f"/api/master-data/tenants/{tenant_id}")
    assert resp.status_code == 200
    assert resp.json()["tenant_name_canonical"] == "Acme"
    assert len(resp.json()["aliases"]) == 1


def test_update_tenant(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
    })
    tenant_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/tenants/{tenant_id}", json={
        "nace_sector": "MANUFACTURING",
    })
    assert resp.status_code == 200
    assert resp.json()["nace_sector"] == "MANUFACTURING"


def test_delete_tenant_cascades(client, db):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/tenants/{tenant_id}")
    assert resp.status_code == 200

    db.expire_all()
    assert db.query(TenantNameAlias).count() == 0


def test_add_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
    })
    tenant_id = resp.json()["id"]

    resp = client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "ACME CSV NAME",
    })
    assert resp.status_code == 200
    assert resp.json()["csv_tenant_name"] == "ACME CSV NAME"


def test_add_alias_duplicate(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "ACME CSV",
    })
    assert resp.status_code == 400


def test_remove_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]
    alias_id = resp.json()["aliases"][0]["id"]

    resp = client.delete(f"/api/master-data/tenants/{tenant_id}/aliases/{alias_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/master-data/tenants/{tenant_id}")
    assert len(resp.json()["aliases"]) == 0


def test_add_alias_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="unmapped_tenant",
        severity="error",
        entity_type="tenant",
        entity_id="UNMAPPED TENANT NAME",
        description="Tenant has no mapping",
        status="open",
    ))
    db.commit()

    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Mapped Tenant",
    })
    tenant_id = resp.json()["id"]

    client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "UNMAPPED TENANT NAME",
    })

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "UNMAPPED TENANT NAME"
    ).first()
    assert inc.status == "resolved"


# â”€â”€ Property Master Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_create_property(client):
    resp = client.post("/api/master-data/properties", json={
        "property_id": "1001",
        "city": "Essen",
        "country": "DE",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["property_id"] == "1001"
    assert data["city"] == "Essen"


def test_create_property_duplicate(client):
    client.post("/api/master-data/properties", json={"property_id": "1001"})
    resp = client.post("/api/master-data/properties", json={"property_id": "1001"})
    assert resp.status_code == 400


def test_list_properties(client):
    for pid in ["1001", "1002", "1003"]:
        client.post("/api/master-data/properties", json={"property_id": pid})
    resp = client.get("/api/master-data/properties")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_properties_search_city(client):
    client.post("/api/master-data/properties", json={"property_id": "1001", "city": "Essen"})
    client.post("/api/master-data/properties", json={"property_id": "1002", "city": "Berlin"})
    client.post("/api/master-data/properties", json={"property_id": "1003", "city": "Essen"})

    resp = client.get("/api/master-data/properties?search=Essen")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_property_partial(client):
    resp = client.post("/api/master-data/properties", json={
        "property_id": "1001",
        "city": "Essen",
        "country": "DE",
    })
    prop_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/properties/{prop_id}", json={
        "city": "Dortmund",
    })
    assert resp.status_code == 200
    assert resp.json()["city"] == "Dortmund"
    assert resp.json()["country"] == "DE"


def test_delete_property(client):
    resp = client.post("/api/master-data/properties", json={"property_id": "1001"})
    prop_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/properties/{prop_id}")
    assert resp.status_code == 200

    resp = client.get("/api/master-data/properties")
    assert len(resp.json()) == 0


def test_create_property_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="missing_metadata",
        severity="warning",
        entity_type="property",
        entity_id="9999",
        description="Property has no metadata",
        status="open",
    ))
    db.commit()

    client.post("/api/master-data/properties", json={"property_id": "9999"})

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "9999"
    ).first()
    assert inc.status == "resolved"


# â”€â”€ Unmapped Endpoint Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_unmapped_returns_grouped(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add_all([
        DataInconsistency(
            upload_id=upload.id, category="unmapped_fund", severity="error",
            entity_type="fund", entity_id="FUND_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="unmapped_tenant", severity="error",
            entity_type="tenant", entity_id="TENANT_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="missing_metadata", severity="warning",
            entity_type="property", entity_id="1001", description="x", status="open",
        ),
    ])
    db.commit()

    resp = client.get("/api/master-data/unmapped")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    types = {item["entity_type"] for item in data}
    assert types == {"fund", "tenant", "property"}


def test_unmapped_filter_by_type(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add_all([
        DataInconsistency(
            upload_id=upload.id, category="unmapped_fund", severity="error",
            entity_type="fund", entity_id="FUND_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="unmapped_tenant", severity="error",
            entity_type="tenant", entity_id="TENANT_A", description="x", status="open",
        ),
    ])
    db.commit()

    resp = client.get("/api/master-data/unmapped?entity_type=fund")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["entity_type"] == "fund"


# â”€â”€ Audit Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_update_creates_audit_entries(client, db):
    resp = client.post("/api/master-data/funds", json={
        "csv_fund_name": "GLIF",
        "bvi_fund_id": "F01",
    })
    fund_id = resp.json()["id"]

    client.patch(f"/api/master-data/funds/{fund_id}", json={
        "bvi_fund_id": "F99",
    })

    db.expire_all()
    audits = db.query(MasterDataAudit).filter(
        MasterDataAudit.table_name == "fund_mapping",
        MasterDataAudit.record_id == fund_id,
        MasterDataAudit.field_name == "bvi_fund_id",
    ).all()
    change_audits = [a for a in audits if a.old_value is not None and a.new_value is not None]
    assert len(change_audits) >= 1
    audit = change_audits[0]
    assert audit.old_value == "F01"
    assert audit.new_value == "F99"

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content frontend/src/app/master-data/page.tsx' in C:\projects\RentRoll
 succeeded in 353ms:
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type FundMapping,
  type TenantMaster,
  type PropertyMaster,
  type UnmappedItem,
  listFundMappings,
  createFundMapping,
  updateFundMapping,
  deleteFundMapping,
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  addTenantAlias,
  removeTenantAlias,
  listProperties,
  createProperty,
  updateProperty,
  deleteProperty,
  listUnmapped,
} from "@/lib/api";

type Tab = "funds" | "tenants" | "properties";

export default function MasterDataPage() {
  const [activeTab, setActiveTab] = useState<Tab>("funds");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Master Data</h1>

      <div className="flex gap-1 mb-6">
        {(["funds", "tenants", "properties"] as Tab[]).map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors ${
              activeTab === tab
                ? "bg-garbe-blau text-white"
                : "bg-garbe-blau-20/40 text-garbe-blau hover:bg-garbe-blau-20"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "funds"
              ? "Funds"
              : tab === "tenants"
                ? "Tenants"
                : "Properties"}
          </button>
        ))}
      </div>

      {activeTab === "funds" && <FundsTab />}
      {activeTab === "tenants" && <TenantsTab />}
      {activeTab === "properties" && <PropertiesTab />}
    </div>
  );
}

// â”€â”€ Funds Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function FundsTab() {
  const [funds, setFunds] = useState<FundMapping[]>([]);
  const [unmapped, setUnmapped] = useState<UnmappedItem[]>([]);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<FundMapping | null>(null);
  const [formName, setFormName] = useState("");
  const [formBviId, setFormBviId] = useState("");
  const [formDesc, setFormDesc] = useState("");

  const load = useCallback(async () => {
    const [f, u] = await Promise.all([
      listFundMappings({ search: search || undefined }),
      listUnmapped("fund"),
    ]);
    setFunds(f);
    setUnmapped(u);
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    await createFundMapping({
      csv_fund_name: formName,
      bvi_fund_id: formBviId || undefined,
      description: formDesc || undefined,
    });
    setShowCreate(false);
    resetForm();
    load();
  };

  const handleUpdate = async () => {
    if (!editTarget) return;
    await updateFundMapping(editTarget.id, {
      bvi_fund_id: formBviId || undefined,
      description: formDesc || undefined,
    });
    setEditTarget(null);
    resetForm();
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this fund mapping?")) return;
    await deleteFundMapping(id);
    load();
  };

  const resetForm = () => {
    setFormName("");
    setFormBviId("");
    setFormDesc("");
  };

  const openCreate = (prefill?: string) => {
    resetForm();
    if (prefill) setFormName(prefill);
    setShowCreate(true);
  };

  const openEdit = (f: FundMapping) => {
    setFormBviId(f.bvi_fund_id || "");
    setFormDesc(f.description || "");
    setEditTarget(f);
  };

  return (
    <>
      <UnmappedBanner
        items={unmapped}
        label="fund"
        onQuickCreate={(id) => openCreate(id)}
      />

      <div className="flex gap-4 mb-4 items-end">
        <SearchInput value={search} onChange={setSearch} />
        <button
          className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors"
          onClick={() => openCreate()}
        >
          Add Fund
        </button>
      </div>

      <DataTable
        headers={["CSV Fund Name", "BVI Fund ID", "Description", "Actions"]}
        rows={funds}
        renderRow={(f, i) => (
          <tr
            key={f.id}
            className={`hover:bg-garbe-neutral/50 ${i % 2 === 1 ? "bg-garbe-offwhite" : ""}`}
          >
            <td className="px-3 py-2 text-garbe-blau font-semibold">
              {f.csv_fund_name}
            </td>
            <td className="px-3 py-2 text-garbe-blau-80">
              {f.bvi_fund_id || "â€”"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-60">
              {f.description || "â€”"}
            </td>
            <td className="px-3 py-2 flex gap-2">
              <ActionButton label="Edit" onClick={() => openEdit(f)} />
              <ActionButton
                label="Delete"
                variant="danger"
                onClick={() => handleDelete(f.id)}
              />
            </td>
          </tr>
        )}
      />

      {/* Create Modal */}
      {showCreate && (
        <Modal title="Add Fund Mapping" onClose={() => setShowCreate(false)}>
          <FormField label="CSV Fund Name">
            <input
              className="form-input"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
          </FormField>
          <FormField label="BVI Fund ID">
            <input
              className="form-input"
              value={formBviId}
              onChange={(e) => setFormBviId(e.target.value)}
            />
          </FormField>
          <FormField label="Description">
            <input
              className="form-input"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setShowCreate(false)}
            onConfirm={handleCreate}
            disabled={!formName}
          />
        </Modal>
      )}

      {/* Edit Modal */}
      {editTarget && (
        <Modal
          title={`Edit: ${editTarget.csv_fund_name}`}
          onClose={() => setEditTarget(null)}
        >
          <FormField label="BVI Fund ID">
            <input
              className="form-input"
              value={formBviId}
              onChange={(e) => setFormBviId(e.target.value)}
            />
          </FormField>
          <FormField label="Description">
            <input
              className="form-input"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setEditTarget(null)}
            onConfirm={handleUpdate}
          />
        </Modal>
      )}
    </>
  );
}

// â”€â”€ Tenants Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function TenantsTab() {
  const [tenants, setTenants] = useState<TenantMaster[]>([]);
  const [unmapped, setUnmapped] = useState<UnmappedItem[]>([]);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<TenantMaster | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [newAliasName, setNewAliasName] = useState("");

  const [formName, setFormName] = useState("");
  const [formBviId, setFormBviId] = useState("");
  const [formNace, setFormNace] = useState("");
  const [formAlias, setFormAlias] = useState("");

  const load = useCallback(async () => {
    const [t, u] = await Promise.all([
      listTenants({ search: search || undefined }),
      listUnmapped("tenant"),
    ]);
    setTenants(t);
    setUnmapped(u);
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    await createTenant({
      tenant_name_canonical: formName,
      bvi_tenant_id: formBviId || undefined,
      nace_sector: formNace || undefined,
      initial_alias: formAlias || undefined,
    });
    setShowCreate(false);
    resetForm();
    load();
  };

  const handleUpdate = async () => {
    if (!editTarget) return;
    await updateTenant(editTarget.id, {
      tenant_name_canonical: formName || undefined,
      bvi_tenant_id: formBviId || undefined,
      nace_sector: formNace || undefined,
    });
    setEditTarget(null);
    resetForm();
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this tenant and all aliases?")) return;
    await deleteTenant(id);
    load();
  };

  const handleAddAlias = async (tenantId: number) => {
    if (!newAliasName) return;
    await addTenantAlias(tenantId, { csv_tenant_name: newAliasName });
    setNewAliasName("");
    load();
  };

  const handleRemoveAlias = async (tenantId: number, aliasId: number) => {
    await removeTenantAlias(tenantId, aliasId);
    load();
  };

  const resetForm = () => {
    setFormName("");
    setFormBviId("");
    setFormNace("");
    setFormAlias("");
  };

  const openCreate = (prefillAlias?: string) => {
    resetForm();
    if (prefillAlias) {
      setFormName(prefillAlias);
      setFormAlias(prefillAlias);
    }
    setShowCreate(true);
  };

  const openEdit = (t: TenantMaster) => {
    setFormName(t.tenant_name_canonical);
    setFormBviId(t.bvi_tenant_id || "");
    setFormNace(t.nace_sector || "");
    setEditTarget(t);
  };

  return (
    <>
      <UnmappedBanner
        items={unmapped}
        label="tenant"
        onQuickCreate={(id) => openCreate(id)}
      />

      <div className="flex gap-4 mb-4 items-end">
        <SearchInput value={search} onChange={setSearch} />
        <button
          className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors"
          onClick={() => openCreate()}
        >
          Add Tenant
        </button>
      </div>

      <div className="bg-white border border-garbe-neutral rounded-lg overflow-x-auto">
        <table className="min-w-full divide-y divide-garbe-neutral text-sm">
          <thead className="bg-garbe-blau-20/40">
            <tr>
              {["Canonical Name", "BVI ID", "NACE", "Aliases", "Actions"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-3 py-2 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider whitespace-nowrap"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-garbe-neutral">
            {tenants.map((t, i) => (
              <>
                <tr
                  key={t.id}
                  className={`hover:bg-garbe-neutral/50 cursor-pointer ${
                    i % 2 === 1 ? "bg-garbe-offwhite" : ""
                  }`}
                  onClick={() =>
                    setExpandedId(expandedId === t.id ? null : t.id)
                  }
                >
                  <td className="px-3 py-2 text-garbe-blau font-semibold">
                    {t.tenant_name_canonical}
                  </td>
                  <td className="px-3 py-2 text-garbe-blau-80">
                    {t.bvi_tenant_id || "â€”"}
                  </td>
                  <td className="px-3 py-2 text-garbe-blau-60">
                    {t.nace_sector || "â€”"}
                  </td>
                  <td className="px-3 py-2 text-garbe-blau-60">
                    {t.aliases.length > 0
                      ? `${t.aliases.length} alias${t.aliases.length > 1 ? "es" : ""}`
                      : "â€”"}
                  </td>
                  <td
                    className="px-3 py-2 flex gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ActionButton label="Edit" onClick={() => openEdit(t)} />
                    <ActionButton
                      label="Delete"
                      variant="danger"
                      onClick={() => handleDelete(t.id)}
                    />
                  </td>
                </tr>
                {expandedId === t.id && (
                  <tr key={`${t.id}-aliases`}>
                    <td colSpan={5} className="px-6 py-3 bg-garbe-offwhite">
                      <div className="text-xs font-semibold text-garbe-blau uppercase tracking-wider mb-2">
                        Aliases
                      </div>
                      {t.aliases.length > 0 ? (
                        <ul className="space-y-1 mb-3">
                          {t.aliases.map((a) => (
                            <li
                              key={a.id}
                              className="flex items-center gap-2 text-sm text-garbe-blau-80"
                            >
                              <span>{a.csv_tenant_name}</span>
                              {a.property_id && (
                                <span className="text-garbe-blau-40">
                                  (prop: {a.property_id})
                                </span>
                              )}
                              <button
                                className="text-xs text-garbe-rot hover:underline"
                                onClick={() =>
                                  handleRemoveAlias(t.id, a.id)
                                }
                              >
                                Remove
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-garbe-blau-40 mb-3">
                          No aliases yet.
                        </p>
                      )}
                      <div className="flex gap-2 items-center">
                        <input
                          className="form-input text-sm flex-1"
                          placeholder="Add alias (CSV tenant name)..."
                          value={newAliasName}
                          onChange={(e) => setNewAliasName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleAddAlias(t.id);
                          }}
                        />
                        <button
                          className="px-3 py-1.5 text-xs font-semibold bg-garbe-grun text-white rounded hover:bg-garbe-grun-80 transition-colors disabled:opacity-40"
                          disabled={!newAliasName}
                          onClick={() => handleAddAlias(t.id)}
                        >
                          Add
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="Add Tenant" onClose={() => setShowCreate(false)}>
          <FormField label="Canonical Name">
            <input
              className="form-input"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
          </FormField>
          <FormField label="BVI Tenant ID">
            <input
              className="form-input"
              value={formBviId}
              onChange={(e) => setFormBviId(e.target.value)}
            />
          </FormField>
          <FormField label="NACE Sector">
            <input
              className="form-input"
              value={formNace}
              onChange={(e) => setFormNace(e.target.value)}
            />
          </FormField>
          <FormField label="Initial Alias (CSV name)">
            <input
              className="form-input"
              value={formAlias}
              onChange={(e) => setFormAlias(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setShowCreate(false)}
            onConfirm={handleCreate}
            disabled={!formName}
          />
        </Modal>
      )}

      {editTarget && (
        <Modal
          title={`Edit: ${editTarget.tenant_name_canonical}`}
          onClose={() => setEditTarget(null)}
        >
          <FormField label="Canonical Name">
            <input
              className="form-input"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
          </FormField>
          <FormField label="BVI Tenant ID">
            <input
              className="form-input"
              value={formBviId}
              onChange={(e) => setFormBviId(e.target.value)}
            />
          </FormField>
          <FormField label="NACE Sector">
            <input
              className="form-input"
              value={formNace}
              onChange={(e) => setFormNace(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setEditTarget(null)}
            onConfirm={handleUpdate}
          />
        </Modal>
      )}
    </>
  );
}

// â”€â”€ Properties Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function PropertiesTab() {
  const [properties, setProperties] = useState<PropertyMaster[]>([]);
  const [unmapped, setUnmapped] = useState<UnmappedItem[]>([]);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<PropertyMaster | null>(null);

  const [formPropId, setFormPropId] = useState("");
  const [formFund, setFormFund] = useState("");
  const [formCity, setFormCity] = useState("");
  const [formStreet, setFormStreet] = useState("");
  const [formCountry, setFormCountry] = useState("");

  const load = useCallback(async () => {
    const [p, u] = await Promise.all([
      listProperties({ search: search || undefined }),
      listUnmapped("property"),
    ]);
    setProperties(p);
    setUnmapped(u);
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    await createProperty({
      property_id: formPropId,
      fund_csv_name: formFund || undefined,
      city: formCity || undefined,
      street: formStreet || undefined,
      country: formCountry || undefined,
    });
    setShowCreate(false);
    resetForm();
    load();
  };

  const handleUpdate = async () => {
    if (!editTarget) return;
    await updateProperty(editTarget.id, {
      fund_csv_name: formFund || undefined,
      city: formCity || undefined,
      street: formStreet || undefined,
      country: formCountry || undefined,
    });
    setEditTarget(null);
    resetForm();
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this property?")) return;
    await deleteProperty(id);
    load();
  };

  const resetForm = () => {
    setFormPropId("");
    setFormFund("");
    setFormCity("");
    setFormStreet("");
    setFormCountry("");
  };

  const openCreate = (prefill?: string) => {
    resetForm();
    if (prefill) setFormPropId(prefill);
    setShowCreate(true);
  };

  const openEdit = (p: PropertyMaster) => {
    setFormFund(p.fund_csv_name || "");
    setFormCity(p.city || "");
    setFormStreet(p.street || "");
    setFormCountry(p.country || "");
    setEditTarget(p);
  };

  return (
    <>
      <UnmappedBanner
        items={unmapped}
        label="property"
        onQuickCreate={(id) => openCreate(id)}
      />

      <div className="flex gap-4 mb-4 items-end">
        <SearchInput value={search} onChange={setSearch} />
        <button
          className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors"
          onClick={() => openCreate()}
        >
          Add Property
        </button>
      </div>

      <DataTable
        headers={[
          "Property ID",
          "Fund",
          "City",
          "Street",
          "Country",
          "Actions",
        ]}
        rows={properties}
        renderRow={(p, i) => (
          <tr
            key={p.id}
            className={`hover:bg-garbe-neutral/50 ${i % 2 === 1 ? "bg-garbe-offwhite" : ""}`}
          >
            <td className="px-3 py-2 text-garbe-blau font-semibold">
              {p.property_id}
            </td>
            <td className="px-3 py-2 text-garbe-blau-80">
              {p.fund_csv_name || "â€”"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-80">{p.city || "â€”"}</td>
            <td className="px-3 py-2 text-garbe-blau-60 max-w-[200px] truncate">
              {p.street || "â€”"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-60">
              {p.country || "â€”"}
            </td>
            <td className="px-3 py-2 flex gap-2">
              <ActionButton label="Edit" onClick={() => openEdit(p)} />
              <ActionButton
                label="Delete"
                variant="danger"
                onClick={() => handleDelete(p.id)}
              />
            </td>
          </tr>
        )}
      />

      {showCreate && (
        <Modal title="Add Property" onClose={() => setShowCreate(false)}>
          <FormField label="Property ID">
            <input
              className="form-input"
              value={formPropId}
              onChange={(e) => setFormPropId(e.target.value)}
            />
          </FormField>
          <FormField label="Fund">
            <input
              className="form-input"
              value={formFund}
              onChange={(e) => setFormFund(e.target.value)}
            />
          </FormField>
          <FormField label="City">
            <input
              className="form-input"
              value={formCity}
              onChange={(e) => setFormCity(e.target.value)}
            />
          </FormField>
          <FormField label="Street">
            <input
              className="form-input"
              value={formStreet}
              onChange={(e) => setFormStreet(e.target.value)}
            />
          </FormField>
          <FormField label="Country">
            <input
              className="form-input"
              value={formCountry}
              onChange={(e) => setFormCountry(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setShowCreate(false)}
            onConfirm={handleCreate}
            disabled={!formPropId}
          />
        </Modal>
      )}

      {editTarget && (
        <Modal
          title={`Edit: ${editTarget.property_id}`}
          onClose={() => setEditTarget(null)}
        >
          <FormField label="Fund">
            <input
              className="form-input"
              value={formFund}
              onChange={(e) => setFormFund(e.target.value)}
            />
          </FormField>
          <FormField label="City">
            <input
              className="form-input"
              value={formCity}
              onChange={(e) => setFormCity(e.target.value)}
            />
          </FormField>
          <FormField label="Street">
            <input
              className="form-input"
              value={formStreet}
              onChange={(e) => setFormStreet(e.target.value)}
            />
          </FormField>
          <FormField label="Country">
            <input
              className="form-input"
              value={formCountry}
              onChange={(e) => setFormCountry(e.target.value)}
            />
          </FormField>
          <ModalActions
            onCancel={() => setEditTarget(null)}
            onConfirm={handleUpdate}
          />
        </Modal>
      )}
    </>
  );
}

// â”€â”€ Shared Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function UnmappedBanner({
  items,
  label,
  onQuickCreate,
}: {
  items: UnmappedItem[];
  label: string;
  onQuickCreate: (id: string) => void;
}) {
  if (items.length === 0) return null;

  const isError = label === "fund" || label === "tenant";
  return (
    <div
      className={`rounded-lg border px-4 py-3 mb-4 ${
        isError
          ? "bg-garbe-rot/10 border-garbe-rot/30"
          : "bg-garbe-ocker/10 border-garbe-ocker/30"
      }`}
    >
      <div
        className={`text-sm font-semibold mb-2 ${isError ? "text-garbe-rot" : "text-garbe-ocker"}`}
      >
        {items.length} unmapped {label}
        {items.length > 1 ? "s" : ""} from uploads
      </div>
      <div className="flex flex-wrap gap-2">
        {items.slice(0, 20).map((item) => (
          <button
            key={item.entity_id}
            className={`text-xs px-2 py-1 rounded font-semibold transition-colors ${
              isError
                ? "bg-garbe-rot/20 text-garbe-rot hover:bg-garbe-rot/30"
                : "bg-garbe-ocker/20 text-garbe-ocker hover:bg-garbe-ocker/30"
            }`}
            onClick={() => onQuickCreate(item.entity_id)}
          >
            + {item.entity_id}
          </button>
        ))}
        {items.length > 20 && (
          <span className="text-xs text-garbe-blau-40 self-center">
            +{items.length - 20} more
          </span>
        )}
      </div>
    </div>
  );
}

function SearchInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex-1">
      <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
        Search
      </label>
      <input
        className="form-input w-full"
        placeholder="Search..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function DataTable<T>({
  headers,
  rows,
  renderRow,
}: {
  headers: string[];
  rows: T[];
  renderRow: (row: T, index: number) => React.ReactNode;
}) {
  if (rows.length === 0) {
    return (
      <p className="text-garbe-blau-40 text-sm">No records found.</p>
    );
  }
  return (
    <div className="bg-white border border-garbe-neutral rounded-lg overflow-x-auto">
      <table className="min-w-full divide-y divide-garbe-neutral text-sm">
        <thead className="bg-garbe-blau-20/40">
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="px-3 py-2 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-garbe-neutral">
          {rows.map((row, i) => renderRow(row, i))}
        </tbody>
      </table>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  variant = "default",
}: {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
}) {
  return (
    <button
      className={`text-xs px-2 py-1 rounded font-semibold transition-colors ${
        variant === "danger"
          ? "text-garbe-rot hover:bg-garbe-rot/10"
          : "text-garbe-blau hover:bg-garbe-blau/10"
      }`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-garbe-blau mb-4">{title}</h3>
        {children}
      </div>
    </div>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  );
}

function ModalActions({
  onCancel,
  onConfirm,
  disabled,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex gap-3 justify-end mt-4">
      <button
        className="px-4 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors"
        onClick={onCancel}
      >
        Cancel
      </button>
      <button
        className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors disabled:opacity-40"
        onClick={onConfirm}
        disabled={disabled}
      >
        Save
      </button>
    </div>
  );
}

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/models/database.py' in C:\projects\RentRoll
 succeeded in 268ms:
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CsvUpload(Base):
    __tablename__ = "csv_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    upload_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    stichtag: Mapped[date | None] = mapped_column(Date)
    fund_label: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="processing")
    row_count: Mapped[int | None] = mapped_column(Integer)
    data_row_count: Mapped[int | None] = mapped_column(Integer)
    summary_row_count: Mapped[int | None] = mapped_column(Integer)
    orphan_row_count: Mapped[int | None] = mapped_column(Integer)
    column_fingerprint: Mapped[str | None] = mapped_column(String(64))
    column_headers_json: Mapped[dict | None] = mapped_column(JSON)
    parser_warnings_json: Mapped[list | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    rows = relationship("RawRentRoll", back_populates="upload", cascade="all, delete-orphan")
    inconsistencies = relationship("DataInconsistency", back_populates="upload", cascade="all, delete-orphan")


class RawRentRoll(Base):
    __tablename__ = "raw_rent_roll"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("csv_uploads.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(20))  # data, property_summary, orphan, total

    fund: Mapped[str | None] = mapped_column(String(100))
    fund_inherited: Mapped[bool] = mapped_column(Boolean, default=False)
    property_id: Mapped[str | None] = mapped_column(String(20))
    property_name: Mapped[str | None] = mapped_column(String(500))
    garbe_office: Mapped[str | None] = mapped_column(String(200))

    unit_id: Mapped[str | None] = mapped_column(String(50))
    unit_type: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(50))
    parking_count: Mapped[int | None] = mapped_column(Integer)
    area_sqm: Mapped[float | None] = mapped_column(Numeric(14, 4))

    lease_id: Mapped[str | None] = mapped_column(String(50))
    tenant_name: Mapped[str | None] = mapped_column(String(500))
    lease_start: Mapped[date | None] = mapped_column(Date)
    lease_end_agreed: Mapped[date | None] = mapped_column(Date)
    lease_end_termination: Mapped[date | None] = mapped_column(Date)
    lease_end_actual: Mapped[date | None] = mapped_column(Date)
    special_termination_notice: Mapped[str | None] = mapped_column(String(100))
    special_termination_date: Mapped[date | None] = mapped_column(Date)
    notice_period: Mapped[str | None] = mapped_column(String(100))
    notice_date: Mapped[date | None] = mapped_column(Date)
    option_duration_months: Mapped[int | None] = mapped_column(Integer)
    option_exercise_deadline: Mapped[date | None] = mapped_column(Date)
    lease_end_after_option: Mapped[date | None] = mapped_column(Date)
    additional_options: Mapped[int | None] = mapped_column(Integer)
    max_lease_term: Mapped[str | None] = mapped_column(String(100))
    wault: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waulb: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waule: Mapped[float | None] = mapped_column(Numeric(10, 4))

    annual_net_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    monthly_net_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    investment_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    rent_free_end: Mapped[date | None] = mapped_column(Date)
    rent_free_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    market_rent_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    erv_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    reversion_potential_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    net_rent_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    market_rent_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    erv_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))

    service_charge_advance: Mapped[float | None] = mapped_column(Numeric(14, 2))
    service_charge_lumpsum: Mapped[float | None] = mapped_column(Numeric(14, 2))
    sc_advance_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    sc_lumpsum_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    total_gross_rent_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    total_gross_rent_per_sqm: Mapped[float | None] = mapped_column(Numeric(14, 4))
    vat_liable: Mapped[str | None] = mapped_column(String(20))

    pct_rent_increase: Mapped[str | None] = mapped_column(String(10))
    increase_percentage: Mapped[float | None] = mapped_column(Numeric(10, 4))
    next_increase_date: Mapped[date | None] = mapped_column(Date)
    escalation_cycles: Mapped[str | None] = mapped_column(String(200))

    index_escalation: Mapped[str | None] = mapped_column(String(10))
    index_type: Mapped[str | None] = mapped_column(String(100))
    threshold: Mapped[str | None] = mapped_column(String(100))
    index_ref_date: Mapped[date | None] = mapped_column(Date)
    passthrough_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    green_lease: Mapped[int | None] = mapped_column(Integer)

    upload = relationship("CsvUpload", back_populates="rows")


class FundMapping(Base):
    __tablename__ = "fund_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    csv_fund_name: Mapped[str] = mapped_column(String(100), unique=True)
    bvi_fund_id: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class TenantMaster(Base):
    __tablename__ = "tenant_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    bvi_tenant_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    tenant_name_canonical: Mapped[str] = mapped_column(String(500))
    nace_sector: Mapped[str | None] = mapped_column(String(100))
    pd_min: Mapped[float | None] = mapped_column(Numeric(10, 6))
    pd_max: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)

    aliases = relationship("TenantNameAlias", back_populates="tenant_master", cascade="all, delete-orphan")


class TenantNameAlias(Base):
    __tablename__ = "tenant_name_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_master_id: Mapped[int] = mapped_column(ForeignKey("tenant_master.id", ondelete="CASCADE"))
    csv_tenant_name: Mapped[str] = mapped_column(String(500))
    property_id: Mapped[str | None] = mapped_column(String(20))

    tenant_master = relationship("TenantMaster", back_populates="aliases")


class PropertyMaster(Base):
    __tablename__ = "property_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[str] = mapped_column(String(20), unique=True)
    fund_csv_name: Mapped[str | None] = mapped_column(String(100))
    predecessor_id: Mapped[str | None] = mapped_column(String(100))
    prop_state: Mapped[str | None] = mapped_column(String(50))
    ownership_type: Mapped[str | None] = mapped_column(String(50))
    land_ownership: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(10))
    region: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(200))
    street: Mapped[str | None] = mapped_column(String(500))
    location_quality: Mapped[str | None] = mapped_column(String(10))

    green_building_vendor: Mapped[str | None] = mapped_column(String(50))
    green_building_cert: Mapped[str | None] = mapped_column(String(50))
    green_building_from: Mapped[date | None] = mapped_column(Date)
    green_building_to: Mapped[date | None] = mapped_column(Date)

    ownership_share: Mapped[float | None] = mapped_column(Numeric(5, 4))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    construction_year: Mapped[int | None] = mapped_column(Integer)
    risk_style: Mapped[str | None] = mapped_column(String(50))
    fair_value: Mapped[float | None] = mapped_column(Numeric(16, 2))
    market_net_yield: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_valuation_date: Mapped[date | None] = mapped_column(Date)
    next_valuation_date: Mapped[date | None] = mapped_column(Date)
    plot_size_sqm: Mapped[float | None] = mapped_column(Numeric(14, 2))
    debt_property: Mapped[float | None] = mapped_column(Numeric(16, 2))
    shareholder_loan: Mapped[float | None] = mapped_column(Numeric(16, 2))

    # ESG / Sustainability
    co2_emissions: Mapped[float | None] = mapped_column(Numeric(10, 2))
    co2_measurement_year: Mapped[int | None] = mapped_column(Integer)
    energy_intensity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    energy_intensity_normalised: Mapped[float | None] = mapped_column(Numeric(10, 2))
    data_quality_energy: Mapped[str | None] = mapped_column(String(50))
    energy_reference_area: Mapped[float | None] = mapped_column(Numeric(14, 2))
    crrem_floor_areas_json: Mapped[dict | None] = mapped_column(JSON)
    exposure_fossil_fuels: Mapped[float | None] = mapped_column(Numeric(10, 4))
    exposure_energy_inefficiency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waste_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    waste_recycled_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    epc_rating: Mapped[str | None] = mapped_column(String(10))

    # Technical Specifications
    tech_clear_height: Mapped[float | None] = mapped_column(Numeric(6, 2))
    tech_floor_load_capacity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    tech_loading_docks: Mapped[int | None] = mapped_column(Integer)
    tech_sprinkler: Mapped[str | None] = mapped_column(String(100))
    tech_lighting: Mapped[str | None] = mapped_column(String(100))
    tech_heating: Mapped[str | None] = mapped_column(String(100))
    maintenance: Mapped[str | None] = mapped_column(String(200))


class DataInconsistency(Base):
    __tablename__ = "data_inconsistencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("csv_uploads.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    field_name: Mapped[str | None] = mapped_column(String(100))
    expected_value: Mapped[str | None] = mapped_column(Text)
    actual_value: Mapped[str | None] = mapped_column(Text)
    deviation_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    upload = relationship("CsvUpload", back_populates="inconsistencies")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_calls_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class MasterDataAudit(Base):
    __tablename__ = "master_data_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[int] = mapped_column(Integer)
    field_name: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[str | None] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    session_id: Mapped[int | None] = mapped_column(Integer)


class ReportingPeriod(Base):
    __tablename__ = "reporting_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    stichtag: Mapped[date] = mapped_column(Date, unique=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("csv_uploads.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    finalized_by: Mapped[str | None] = mapped_column(String(100))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SnapshotPropertyMaster(Base):
    __tablename__ = "snapshot_property_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    property_id: Mapped[str] = mapped_column(String(20))
    fund_csv_name: Mapped[str | None] = mapped_column(String(100))
    predecessor_id: Mapped[str | None] = mapped_column(String(100))
    prop_state: Mapped[str | None] = mapped_column(String(50))
    ownership_type: Mapped[str | None] = mapped_column(String(50))
    land_ownership: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(10))
    region: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(200))
    street: Mapped[str | None] = mapped_column(String(500))
    location_quality: Mapped[str | None] = mapped_column(String(10))
    green_building_vendor: Mapped[str | None] = mapped_column(String(50))
    green_building_cert: Mapped[str | None] = mapped_column(String(50))
    green_building_from: Mapped[date | None] = mapped_column(Date)
    green_building_to: Mapped[date | None] = mapped_column(Date)
    ownership_share: Mapped[float | None] = mapped_column(Numeric(5, 4))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    construction_year: Mapped[int | None] = mapped_column(Integer)
    risk_style: Mapped[str | None] = mapped_column(String(50))
    fair_value: Mapped[float | None] = mapped_column(Numeric(16, 2))
    market_net_yield: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_valuation_date: Mapped[date | None] = mapped_column(Date)
    next_valuation_date: Mapped[date | None] = mapped_column(Date)
    plot_size_sqm: Mapped[float | None] = mapped_column(Numeric(14, 2))
    debt_property: Mapped[float | None] = mapped_column(Numeric(16, 2))
    shareholder_loan: Mapped[float | None] = mapped_column(Numeric(16, 2))
    co2_emissions: Mapped[float | None] = mapped_column(Numeric(10, 2))
    co2_measurement_year: Mapped[int | None] = mapped_column(Integer)
    energy_intensity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    energy_intensity_normalised: Mapped[float | None] = mapped_column(Numeric(10, 2))
    data_quality_energy: Mapped[str | None] = mapped_column(String(50))
    energy_reference_area: Mapped[float | None] = mapped_column(Numeric(14, 2))
    crrem_floor_areas_json: Mapped[dict | None] = mapped_column(JSON)
    exposure_fossil_fuels: Mapped[float | None] = mapped_column(Numeric(10, 4))
    exposure_energy_inefficiency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waste_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    waste_recycled_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    epc_rating: Mapped[str | None] = mapped_column(String(10))
    tech_clear_height: Mapped[float | None] = mapped_column(Numeric(6, 2))
    tech_floor_load_capacity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    tech_loading_docks: Mapped[int | None] = mapped_column(Integer)
    tech_sprinkler: Mapped[str | None] = mapped_column(String(100))
    tech_lighting: Mapped[str | None] = mapped_column(String(100))
    tech_heating: Mapped[str | None] = mapped_column(String(100))
    maintenance: Mapped[str | None] = mapped_column(String(200))


class SnapshotTenantMaster(Base):
    __tablename__ = "snapshot_tenant_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    bvi_tenant_id: Mapped[str | None] = mapped_column(String(50))
    tenant_name_canonical: Mapped[str] = mapped_column(String(500))
    nace_sector: Mapped[str | None] = mapped_column(String(100))
    pd_min: Mapped[float | None] = mapped_column(Numeric(10, 6))
    pd_max: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)


class SnapshotTenantNameAlias(Base):
    __tablename__ = "snapshot_tenant_name_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    snapshot_tenant_master_id: Mapped[int] = mapped_column(
        ForeignKey("snapshot_tenant_master.id", ondelete="CASCADE")
    )
    csv_tenant_name: Mapped[str] = mapped_column(String(500))
    property_id: Mapped[str | None] = mapped_column(String(20))


class SnapshotFundMapping(Base):
    __tablename__ = "snapshot_fund_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    csv_fund_name: Mapped[str] = mapped_column(String(100))
    bvi_fund_id: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem -Recurse backend/app | Select-String -Pattern "master-data|MasterDataAudit|log_changes|master_data" | Select-Object Path,LineNumber,Line' in C:\projects\RentRoll
 succeeded in 395ms:

Path                                                                         LineNumber Line                           
----                                                                         ---------- ----                           
C:\projects\RentRoll\backend\app\main.py                                              8 from app.api.master_data imp...
C:\projects\RentRoll\backend\app\main.py                                             37 app.include_router(master_da...
C:\projects\RentRoll\backend\app\api\master_data.py                                   8 from app.core.audit import l...
C:\projects\RentRoll\backend\app\api\master_data.py                                  32 router = APIRouter(tags=["ma...
C:\projects\RentRoll\backend\app\api\master_data.py                                  76 @router.get("/master-data/fu...
C:\projects\RentRoll\backend\app\api\master_data.py                                  89 @router.post("/master-data/f...
C:\projects\RentRoll\backend\app\api\master_data.py                                 107 @router.patch("/master-data/...
C:\projects\RentRoll\backend\app\api\master_data.py                                 117     log_changes(db, "fund_ma...
C:\projects\RentRoll\backend\app\api\master_data.py                                 123 @router.delete("/master-data...
C:\projects\RentRoll\backend\app\api\master_data.py                                 136 @router.get("/master-data/te...
C:\projects\RentRoll\backend\app\api\master_data.py                                 161 @router.post("/master-data/t...
C:\projects\RentRoll\backend\app\api\master_data.py                                 182 @router.get("/master-data/te...
C:\projects\RentRoll\backend\app\api\master_data.py                                 195 @router.patch("/master-data/...
C:\projects\RentRoll\backend\app\api\master_data.py                                 205     log_changes(db, "tenant_...
C:\projects\RentRoll\backend\app\api\master_data.py                                 211 @router.delete("/master-data...
C:\projects\RentRoll\backend\app\api\master_data.py                                 230     "/master-data/tenants/{t...
C:\projects\RentRoll\backend\app\api\master_data.py                                 257 @router.delete("/master-data...
C:\projects\RentRoll\backend\app\api\master_data.py                                 276 @router.get("/master-data/pr...
C:\projects\RentRoll\backend\app\api\master_data.py                                 292 @router.post("/master-data/p...
C:\projects\RentRoll\backend\app\api\master_data.py                                 310 @router.get("/master-data/pr...
C:\projects\RentRoll\backend\app\api\master_data.py                                 318 @router.patch("/master-data/...
C:\projects\RentRoll\backend\app\api\master_data.py                                 328     log_changes(db, "propert...
C:\projects\RentRoll\backend\app\api\master_data.py                                 334 @router.delete("/master-data...
C:\projects\RentRoll\backend\app\api\master_data.py                                 354 @router.get("/master-data/un...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc          7 HTTPException)�or_)�Sess...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         18    �str)�formats   "�3C:...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         27 � rZ   z/master-data/fun...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         39 � ��C�#5�d�6H�6H�5I�IY�...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         50 �6�6�+�w�'�D���C�!9�:�...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         70 � ��%6��8J�8J�K��I�I�K...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         83 delete_tenantr�   �   s�   �...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc         90  �F�F�5�M��H�H�J��R�!2...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc        101 �����	�E�1�1�=�%�BS�...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc        110 � ��C�:�d�.>�.>�-?�?O�!...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc        121 �6�6�.�+�.�D���C�!5�6�...
C:\projects\RentRoll\backend\app\core\audit.py                                        6 from app.models.database imp...
C:\projects\RentRoll\backend\app\core\audit.py                                       25 def log_changes(               
C:\projects\RentRoll\backend\app\core\audit.py                                       33 ) -> list[MasterDataAudit]:    
C:\projects\RentRoll\backend\app\core\audit.py                                       38             entry = MasterDa...
C:\projects\RentRoll\backend\app\core\audit.py                                       59 ) -> list[MasterDataAudit]:    
C:\projects\RentRoll\backend\app\core\audit.py                                       63             entry = MasterDa...
C:\projects\RentRoll\backend\app\core\audit.py                                       84 ) -> list[MasterDataAudit]:    
C:\projects\RentRoll\backend\app\core\audit.py                                       88             entry = MasterDa...
C:\projects\RentRoll\backend\app\core\__pycache__\audit.cpython-314.pyc               6  lltRR R lltR	# ...
C:\projects\RentRoll\backend\app\core\__pycache__\audit.cpython-314.pyc              30    �log_changesr7      s� ...
C:\projects\RentRoll\backend\app\models\database.py                                 257 class MasterDataAudit(Base):   
C:\projects\RentRoll\backend\app\models\database.py                                 258     __tablename__ = "master_...
C:\projects\RentRoll\backend\app\models\__pycache__\database.cpython-313.pyc        219 5      r\\S-     \	S...
C:\projects\RentRoll\backend\app\models\__pycache__\database.cpython-314.pyc        166 ]! ]4      t]! ]! ^24...
C:\projects\RentRoll\backend\app\models\__pycache__\database.cpython-314.pyc        171 changed_atr  r�   )r:   r...
C:\projects\RentRoll\backend\app\__pycache__\main.cpython-314.pyc                    22 contextlibr   �fastapir  ...



exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content .gitignore' in C:\projects\RentRoll
 succeeded in 286ms:
# === Python ===
__pycache__/
*.py[codz]
*$py.class
*.so
*.egg-info/
*.egg
dist/
build/
.eggs/

# Virtual environments
.venv/
venv/
env/

# Test / coverage
.pytest_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml

# Type checkers
.mypy_cache/
.pytype/
.pyre/

# Celery
celerybeat-schedule
celerybeat.pid

# Ruff
.ruff_cache/

# === Node / Next.js ===
node_modules/
.next/
out/
.turbo/

# === Environment & secrets ===
.env
.env.*
!.env.example

# === IDE ===
.idea/
.vscode/
*.swp
*.swo
*~

# === OS ===
.DS_Store
Thumbs.db
desktop.ini

# === Database ===
*.sqlite3
*.sqlite3-journal
*.db

# === Project-specific ===

# Uploads (keep directory, ignore uploaded files)
uploads/*
!uploads/.gitkeep

# Generated exports
exports/

# Claude Code local settings
.claude/

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'pytest -q backend/tests/test_audit.py backend/tests/test_master_data_api.py' in C:\projects\RentRoll
2026-04-24T12:44:18.383035Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 3.9 seconds
Total output lines: 1874
Output:
......EEEEEEEEEEEEEEEEEEEEEEEEEEEEEE                                     [100%]
=================================== ERRORS ====================================
_____________________ ERROR at setup of test_create_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________________ ERROR at setup of test_create_fund_duplicate _________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
______________________ ERROR at setup of test_list_funds ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
__________________ ERROR at setup of test_list_funds_search ___________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_update_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________________ ERROR at setup of test_update_fund_not_found _________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_delete_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__…14596 tokens truncated…
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
___________________ ERROR at setup of test_delete_property ____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________ ERROR at setup of test_create_property_resolves_inconsistency ________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_unmapped_returns_grouped _______________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_unmapped_filter_by_type ________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________ ERROR at setup of test_update_creates_audit_entries _____________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
============================== warnings summary ===============================
..\..\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:475
  C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:475: PytestCacheWarning: could not create cache path C:\projects\RentRoll\.pytest_cache\v\cache\nodeids: [WinError 5] Zugriff verweigert: 'C:\\projects\\RentRoll\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

..\..\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:429
  C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:429: PytestCacheWarning: could not create cache path C:\projects\RentRoll\.pytest_cache\v\cache\lastfailed: [WinError 5] Zugriff verweigert: 'C:\\projects\\RentRoll\\.pytest_cache\\v\\cache'
    config.cache.set("cache/lastfailed", self.lastfailed)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR backend/tests/test_master_data_api.py::test_create_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_create_fund_duplicate - Run...
ERROR backend/tests/test_master_data_api.py::test_list_funds - RuntimeError: ...
ERROR backend/tests/test_master_data_api.py::test_list_funds_search - Runtime...
ERROR backend/tests/test_master_data_api.py::test_update_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_update_fund_not_found - Run...
ERROR backend/tests/test_master_data_api.py::test_delete_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_create_fund_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_create_tenant - RuntimeErro...
ERROR backend/tests/test_master_data_api.py::test_create_tenant_with_alias - ...
ERROR backend/tests/test_master_data_api.py::test_list_tenants - RuntimeError...
ERROR backend/tests/test_master_data_api.py::test_list_tenants_search_canonical
ERROR backend/tests/test_master_data_api.py::test_list_tenants_search_by_alias
ERROR backend/tests/test_master_data_api.py::test_get_tenant_detail - Runtime...
ERROR backend/tests/test_master_data_api.py::test_update_tenant - RuntimeErro...
ERROR backend/tests/test_master_data_api.py::test_delete_tenant_cascades - Ru...
ERROR backend/tests/test_master_data_api.py::test_add_alias - RuntimeError: F...
ERROR backend/tests/test_master_data_api.py::test_add_alias_duplicate - Runti...
ERROR backend/tests/test_master_data_api.py::test_remove_alias - RuntimeError...
ERROR backend/tests/test_master_data_api.py::test_add_alias_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_create_property - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_create_property_duplicate
ERROR backend/tests/test_master_data_api.py::test_list_properties - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_list_properties_search_city
ERROR backend/tests/test_master_data_api.py::test_update_property_partial - R...
ERROR backend/tests/test_master_data_api.py::test_delete_property - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_create_property_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_unmapped_returns_grouped - ...
ERROR backend/tests/test_master_data_api.py::test_unmapped_filter_by_type - R...
ERROR backend/tests/test_master_data_api.py::test_update_creates_audit_entries
6 passed, 2 warnings, 30 errors in 2.89s

 exited 1 in 3856ms:
......EEEEEEEEEEEEEEEEEEEEEEEEEEEEEE                                     [100%]
=================================== ERRORS ====================================
_____________________ ERROR at setup of test_create_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________________ ERROR at setup of test_create_fund_duplicate _________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
______________________ ERROR at setup of test_list_funds ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
__________________ ERROR at setup of test_list_funds_search ___________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_update_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________________ ERROR at setup of test_update_fund_not_found _________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_delete_fund ______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
__________ ERROR at setup of test_create_fund_resolves_inconsistency __________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
____________________ ERROR at setup of test_create_tenant _____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_create_tenant_with_alias _______________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_list_tenants _____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
____________ ERROR at setup of test_list_tenants_search_canonical _____________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________ ERROR at setup of test_list_tenants_search_by_alias _____________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
__________________ ERROR at setup of test_get_tenant_detail ___________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
____________________ ERROR at setup of test_update_tenant _____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________________ ERROR at setup of test_delete_tenant_cascades ________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
______________________ ERROR at setup of test_add_alias _______________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_________________ ERROR at setup of test_add_alias_duplicate __________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________________ ERROR at setup of test_remove_alias _____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
___________ ERROR at setup of test_add_alias_resolves_inconsistency ___________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
___________________ ERROR at setup of test_create_property ____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
______________ ERROR at setup of test_create_property_duplicate _______________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
___________________ ERROR at setup of test_list_properties ____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________ ERROR at setup of test_list_properties_search_city ______________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_update_property_partial ________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
___________________ ERROR at setup of test_delete_property ____________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
________ ERROR at setup of test_create_property_resolves_inconsistency ________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_unmapped_returns_grouped _______________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_______________ ERROR at setup of test_unmapped_filter_by_type ________________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
_____________ ERROR at setup of test_update_creates_audit_entries _____________

    @pytest.fixture(autouse=True)
    def setup_db():
        Base.metadata.create_all(test_engine)
    
>       from app.api.upload import set_session_factory

backend\tests\test_master_data_api.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend\app\api\upload.py:118: in <module>
    @router.post("/upload", response_model=UploadResponse)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1446: in decorator
    self.add_api_route(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:1382: in add_api_route
    route = route_class(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\routing.py:945: in __init__
    self.dependant = get_dependant(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:309: in get_dependant
    param_details = analyze_param(
C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:532: in analyze_param
    ensure_multipart_is_installed()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    def ensure_multipart_is_installed() -> None:
        try:
            from python_multipart import __version__
    
            # Import an attribute that can be mocked/deleted in testing
            assert __version__ > "0.0.12"
        except (ImportError, AssertionError):
            try:
                # __version__ is available in both multiparts, and can be mocked
                from multipart import __version__  # type: ignore[no-redef,import-untyped]
    
                assert __version__
                try:
                    # parse_options_header is only available in the right multipart
                    from multipart.multipart import (  # type: ignore[import-untyped]
                        parse_options_header,
                    )
    
                    assert parse_options_header
                except ImportError:
                    logger.error(multipart_incorrect_install_error)
                    raise RuntimeError(multipart_incorrect_install_error) from None
            except ImportError:
                logger.error(multipart_not_installed_error)
>               raise RuntimeError(multipart_not_installed_error) from None
E               RuntimeError: Form data requires "python-multipart" to be installed. 
E               You can install "python-multipart" with: 
E               
E               pip install python-multipart

C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\dependencies\utils.py:118: RuntimeError
----------------------------- Captured log setup ------------------------------
ERROR    fastapi:utils.py:117 Form data requires "python-multipart" to be installed. 
You can install "python-multipart" with: 

pip install python-multipart
============================== warnings summary ===============================
..\..\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:475
  C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:475: PytestCacheWarning: could not create cache path C:\projects\RentRoll\.pytest_cache\v\cache\nodeids: [WinError 5] Zugriff verweigert: 'C:\\projects\\RentRoll\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

..\..\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:429
  C:\Users\banho\AppData\Local\Programs\Python\Python313\Lib\site-packages\_pytest\cacheprovider.py:429: PytestCacheWarning: could not create cache path C:\projects\RentRoll\.pytest_cache\v\cache\lastfailed: [WinError 5] Zugriff verweigert: 'C:\\projects\\RentRoll\\.pytest_cache\\v\\cache'
    config.cache.set("cache/lastfailed", self.lastfailed)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR backend/tests/test_master_data_api.py::test_create_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_create_fund_duplicate - Run...
ERROR backend/tests/test_master_data_api.py::test_list_funds - RuntimeError: ...
ERROR backend/tests/test_master_data_api.py::test_list_funds_search - Runtime...
ERROR backend/tests/test_master_data_api.py::test_update_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_update_fund_not_found - Run...
ERROR backend/tests/test_master_data_api.py::test_delete_fund - RuntimeError:...
ERROR backend/tests/test_master_data_api.py::test_create_fund_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_create_tenant - RuntimeErro...
ERROR backend/tests/test_master_data_api.py::test_create_tenant_with_alias - ...
ERROR backend/tests/test_master_data_api.py::test_list_tenants - RuntimeError...
ERROR backend/tests/test_master_data_api.py::test_list_tenants_search_canonical
ERROR backend/tests/test_master_data_api.py::test_list_tenants_search_by_alias
ERROR backend/tests/test_master_data_api.py::test_get_tenant_detail - Runtime...
ERROR backend/tests/test_master_data_api.py::test_update_tenant - RuntimeErro...
ERROR backend/tests/test_master_data_api.py::test_delete_tenant_cascades - Ru...
ERROR backend/tests/test_master_data_api.py::test_add_alias - RuntimeError: F...
ERROR backend/tests/test_master_data_api.py::test_add_alias_duplicate - Runti...
ERROR backend/tests/test_master_data_api.py::test_remove_alias - RuntimeError...
ERROR backend/tests/test_master_data_api.py::test_add_alias_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_create_property - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_create_property_duplicate
ERROR backend/tests/test_master_data_api.py::test_list_properties - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_list_properties_search_city
ERROR backend/tests/test_master_data_api.py::test_update_property_partial - R...
ERROR backend/tests/test_master_data_api.py::test_delete_property - RuntimeEr...
ERROR backend/tests/test_master_data_api.py::test_create_property_resolves_inconsistency
ERROR backend/tests/test_master_data_api.py::test_unmapped_returns_grouped - ...
ERROR backend/tests/test_master_data_api.py::test_unmapped_filter_by_type - R...
ERROR backend/tests/test_master_data_api.py::test_update_creates_audit_entries
6 passed, 2 warnings, 30 errors in 2.89s

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-ChildItem -Recurse backend/app | Select-String -Pattern \"unmapped_fund|unmapped_tenant|missing_metadata|category=\\\"|category ='\" | Select-Object Path,LineNumber,Line" in C:\projects\RentRoll
2026-04-24T12:44:22.326494Z ERROR codex_core::tools::router: error=Exit code: 1
Wall time: 0.3 seconds
Output:
Die Zeichenfolge hat kein Abschlusszeichen: '.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : TerminatorExpectedAtEndOfString
 

 exited 1 in 303ms:
Die Zeichenfolge hat kein Abschlusszeichen: '.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : TerminatorExpectedAtEndOfString
 

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-ChildItem -Recurse backend/app | Select-String -Pattern "unmapped_fund","unmapped_tenant","missing_metadata" | Select-Object Path,LineNumber,Line' in C:\projects\RentRoll
 succeeded in 322ms:

Path                                                                                     LineNumber Line               
----                                                                                     ---------- ----               
C:\projects\RentRoll\backend\app\api\master_data.py                                             101     _resolve_inc...
C:\projects\RentRoll\backend\app\api\master_data.py                                             175         _resolve...
C:\projects\RentRoll\backend\app\api\master_data.py                                             251     _resolve_inc...
C:\projects\RentRoll\backend\app\api\master_data.py                                             304     _resolve_inc...
C:\projects\RentRoll\backend\app\api\master_data.py                                             348     "unmapped_fu...
C:\projects\RentRoll\backend\app\api\master_data.py                                             349     "unmapped_te...
C:\projects\RentRoll\backend\app\api\master_data.py                                             350     "missing_met...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc                     36 unmapped_fund� )...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc                     61 tenant_master)�...
C:\projects\RentRoll\backend\app\api\__pycache__\master_data.cpython-314.pyc                    108 Property 'r~   �...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  34             "unm...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  35             "unm...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  36             "mis...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  42     results.exte...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  43     results.exte...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                  44     results.exte...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 138 def _detect_unma...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 162                 ...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 173 def _detect_unma...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 196                 ...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 207 def _detect_miss...
C:\projects\RentRoll\backend\app\core\inconsistency_detector.py                                 230                 ...
C:\projects\RentRoll\backend\app\core\__pycache__\inconsistency_detector.cpython-313.pyc         19                 ...
C:\projects\RentRoll\backend\app\core\__pycache__\inconsistency_detector.cpython-313.pyc         20 unmapped_fund�m...
C:\projects\RentRoll\backend\app\core\__pycache__\inconsistency_detector.cpython-314.pyc         10                 ...
C:\projects\RentRoll\backend\app\core\__pycache__\inconsistency_detector.cpython-314.pyc         11 unmapped_fund�m...



exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/core/inconsistency_detector.py' in C:\projects\RentRoll
 succeeded in 308ms:
import re
from decimal import Decimal

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.database import (
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantNameAlias,
)

SUMMARY_PROP_RE = re.compile(r"^(\d+)\s*-\s*")

AGGREGATION_FIELDS = [
    ("area_sqm", "Area (sqm)"),
    ("annual_net_rent", "Annual net rent"),
    ("monthly_net_rent", "Monthly net rent"),
    ("parking_count", "Parking count"),
    ("market_rent_monthly", "Market rent (monthly)"),
    ("erv_monthly", "ERV (monthly)"),
]

TOLERANCE_PCT = 1.0


def detect_inconsistencies(db: Session, upload_id: int) -> list[DataInconsistency]:
    db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_id,
        DataInconsistency.category.in_([
            "aggregation_mismatch",
            "unmapped_tenant",
            "unmapped_fund",
            "missing_metadata",
        ]),
    ).delete(synchronize_session=False)

    results: list[DataInconsistency] = []
    results.extend(_detect_aggregation_mismatches(db, upload_id))
    results.extend(_detect_unmapped_tenants(db, upload_id))
    results.extend(_detect_unmapped_funds(db, upload_id))
    results.extend(_detect_missing_metadata(db, upload_id))
    return results


def _detect_aggregation_mismatches(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    agg_query = (
        db.query(
            RawRentRoll.property_id,
            func.sum(RawRentRoll.area_sqm).label("area_sqm"),
            func.sum(RawRentRoll.annual_net_rent).label("annual_net_rent"),
            func.sum(RawRentRoll.monthly_net_rent).label("monthly_net_rent"),
            func.sum(RawRentRoll.parking_count).label("parking_count"),
            func.sum(RawRentRoll.market_rent_monthly).label("market_rent_monthly"),
            func.sum(RawRentRoll.erv_monthly).label("erv_monthly"),
        )
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .group_by(RawRentRoll.property_id)
        .all()
    )

    aggregated = {}
    for row in agg_query:
        aggregated[row.property_id] = {
            "area_sqm": row.area_sqm,
            "annual_net_rent": row.annual_net_rent,
            "monthly_net_rent": row.monthly_net_rent,
            "parking_count": row.parking_count,
            "market_rent_monthly": row.market_rent_monthly,
            "erv_monthly": row.erv_monthly,
        }

    summary_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type == "property_summary",
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for srow in summary_rows:
        m = SUMMARY_PROP_RE.match(srow.fund or "")
        if not m:
            continue
        prop_id = m.group(1)
        agg = aggregated.get(prop_id)
        if not agg:
            continue

        for field, label in AGGREGATION_FIELDS:
            summary_val = getattr(srow, field, None)
            agg_val = agg.get(field)

            if summary_val is None or agg_val is None:
                continue

            s = float(summary_val) if isinstance(summary_val, Decimal) else float(summary_val or 0)
            a = float(agg_val) if isinstance(agg_val, Decimal) else float(agg_val or 0)

            if s == 0 and a == 0:
                continue

            if s == 0:
                deviation = 100.0
            else:
                deviation = abs(a - s) / abs(s) * 100
            if deviation > TOLERANCE_PCT:
                results.append(DataInconsistency(
                    upload_id=upload_id,
                    category="aggregation_mismatch",
                    severity="warning",
                    entity_type="property",
                    entity_id=prop_id,
                    field_name=field,
                    expected_value=str(round(s, 2)),
                    actual_value=str(round(a, 2)),
                    deviation_pct=round(deviation, 2),
                    description=(
                        f"{label} mismatch for property {prop_id}: "
                        f"summary={round(s, 2)}, aggregated={round(a, 2)} "
                        f"(deviation {round(deviation, 1)}%)"
                    ),
                    status="open",
                ))

    return results


def _detect_unmapped_tenants(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    tenant_names = (
        db.query(distinct(RawRentRoll.tenant_name))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.tenant_name.isnot(None),
            RawRentRoll.tenant_name != "LEERSTAND",
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (name,) in tenant_names:
        alias = (
            db.query(TenantNameAlias)
            .filter(TenantNameAlias.csv_tenant_name == name)
            .first()
        )
        if alias is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="unmapped_tenant",
                severity="error",
                entity_type="tenant",
                entity_id=name,
                description=f"Tenant '{name}' has no mapping in tenant_name_alias",
                status="open",
            ))

    return results


def _detect_unmapped_funds(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    fund_names = (
        db.query(distinct(RawRentRoll.fund))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.fund.isnot(None),
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (name,) in fund_names:
        mapping = (
            db.query(FundMapping)
            .filter(FundMapping.csv_fund_name == name)
            .first()
        )
        if mapping is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="unmapped_fund",
                severity="error",
                entity_type="fund",
                entity_id=name,
                description=f"Fund '{name}' has no mapping in fund_mapping",
                status="open",
            ))

    return results


def _detect_missing_metadata(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    property_ids = (
        db.query(distinct(RawRentRoll.property_id))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.property_id.isnot(None),
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (prop_id,) in property_ids:
        pm = (
            db.query(PropertyMaster)
            .filter(PropertyMaster.property_id == prop_id)
            .first()
        )
        if pm is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="missing_metadata",
                severity="warning",
                entity_type="property",
                entity_id=prop_id,
                description=f"Property '{prop_id}' has no entry in property_master",
                status="open",
            ))

    return results

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content frontend/src/lib/api.ts' in C:\projects\RentRoll
 succeeded in 311ms:
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
  body: { bvi_fund_id?: string; description?: string }
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
    bvi_tenant_id?: string;
    nace_sector?: string;
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

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/api/inconsistencies.py' in C:\projects\RentRoll
 succeeded in 279ms:
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database import CsvUpload, DataInconsistency
from app.models.schemas import InconsistencyListItem, InconsistencySummary, InconsistencyUpdate

router = APIRouter(tags=["inconsistencies"])


@router.get("/inconsistencies", response_model=list[InconsistencyListItem])
def list_inconsistencies(
    upload_id: int | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(DataInconsistency)
    if upload_id is not None:
        query = query.filter(DataInconsistency.upload_id == upload_id)
    if category:
        query = query.filter(DataInconsistency.category == category)
    if severity:
        query = query.filter(DataInconsistency.severity == severity)
    if status:
        query = query.filter(DataInconsistency.status == status)

    items = (
        query.order_by(DataInconsistency.created_at.desc(), DataInconsistency.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items


@router.get("/inconsistencies/summary", response_model=InconsistencySummary)
def inconsistency_summary(
    upload_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(DataInconsistency)
    if upload_id is not None:
        query = query.filter(DataInconsistency.upload_id == upload_id)

    rows = query.all()
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    has_blocking = False

    for r in rows:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.severity == "error" and r.status == "open":
            has_blocking = True

    return InconsistencySummary(
        total=len(rows),
        by_severity=by_severity,
        by_category=by_category,
        by_status=by_status,
        has_blocking_errors=has_blocking,
    )


@router.get("/inconsistencies/{inconsistency_id}", response_model=InconsistencyListItem)
def get_inconsistency(
    inconsistency_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(DataInconsistency, inconsistency_id)
    if not item:
        raise HTTPException(404, "Inconsistency not found")
    return item


@router.patch("/inconsistencies/{inconsistency_id}", response_model=InconsistencyListItem)
def update_inconsistency(
    inconsistency_id: int,
    body: InconsistencyUpdate,
    db: Session = Depends(get_db),
):
    item = db.get(DataInconsistency, inconsistency_id)
    if not item:
        raise HTTPException(404, "Inconsistency not found")

    valid_statuses = {"open", "resolved", "acknowledged", "ignored"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    item.status = body.status
    if body.resolution_note is not None:
        item.resolution_note = body.resolution_note
    if body.resolved_by is not None:
        item.resolved_by = body.resolved_by

    if body.status in ("resolved", "acknowledged", "ignored"):
        item.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(item)
    return item


@router.post("/inconsistencies/{upload_id}/recheck")
def recheck_inconsistencies(
    upload_id: int,
    db: Session = Depends(get_db),
):
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")

    from app.core.inconsistency_detector import detect_inconsistencies
    detected = detect_inconsistencies(db, upload_id)
    db.add_all(detected)
    db.commit()

    return {"message": f"Recheck complete. {len(detected)} inconsistencies detected.", "count": len(detected)}

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/models/schemas.py -TotalCount 140' in C:\projects\RentRoll
 succeeded in 288ms:
from datetime import date, datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str


class UploadDetail(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    stichtag: date | None
    fund_label: str | None
    status: str
    row_count: int | None
    data_row_count: int | None
    summary_row_count: int | None
    orphan_row_count: int | None
    column_fingerprint: str | None
    parser_warnings_json: list | None
    error_message: str | None

    model_config = {"from_attributes": True}


class UploadListItem(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    stichtag: date | None
    status: str
    row_count: int | None

    model_config = {"from_attributes": True}


class RawRentRollRow(BaseModel):
    id: int
    row_number: int
    row_type: str
    fund: str | None
    fund_inherited: bool
    property_id: str | None
    property_name: str | None
    unit_id: str | None
    unit_type: str | None
    tenant_name: str | None
    area_sqm: float | None
    annual_net_rent: float | None
    monthly_net_rent: float | None
    market_rent_monthly: float | None
    lease_start: date | None
    lease_end_actual: date | None

    model_config = {"from_attributes": True}


class ParseStats(BaseModel):
    total_rows: int
    data_rows: int
    summary_rows: int
    orphan_rows: int
    total_rows_found: int
    funds: list[str]
    properties: int
    warnings: list[str]


class InconsistencyListItem(BaseModel):
    id: int
    upload_id: int
    category: str
    severity: str
    entity_type: str | None
    entity_id: str | None
    field_name: str | None
    expected_value: str | None
    actual_value: str | None
    deviation_pct: float | None
    description: str
    status: str
    resolution_note: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InconsistencyUpdate(BaseModel):
    status: str
    resolution_note: str | None = None
    resolved_by: str | None = None


class InconsistencySummary(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_status: dict[str, int]
    has_blocking_errors: bool


# --- Fund Mapping ---

class FundMappingCreate(BaseModel):
    csv_fund_name: str
    bvi_fund_id: str | None = None
    description: str | None = None


class FundMappingUpdate(BaseModel):
    bvi_fund_id: str | None = None
    description: str | None = None


class FundMappingResponse(BaseModel):
    id: int
    csv_fund_name: str
    bvi_fund_id: str | None
    description: str | None

    model_config = {"from_attributes": True}


# --- Tenant ---

class TenantAliasCreate(BaseModel):
    csv_tenant_name: str
    property_id: str | None = None


class TenantAliasResponse(BaseModel):
    id: int
    tenant_master_id: int

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'Get-Content backend/app/api/upload.py' in C:\projects\RentRoll
 succeeded in 305ms:
import os
import traceback
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.schema_validator import validate_schema
from app.database import SessionLocal, get_db
from app.models.database import CsvUpload, DataInconsistency, RawRentRoll
from app.models.schemas import UploadDetail, UploadListItem, UploadResponse
from app.parsers.garbe_mieterliste import GarbeMieterliste

router = APIRouter(tags=["upload"])

_session_factory = None


def get_session_factory():
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    return SessionLocal


def set_session_factory(factory):
    global _session_factory
    _session_factory = factory


def _process_upload(upload_id: int, file_content: bytes, filename: str):
    db = get_session_factory()()
    try:
        upload = db.get(CsvUpload, upload_id)
        if not upload:
            return

        parser = GarbeMieterliste()

        if not GarbeMieterliste.detect(file_content, filename):
            upload.status = "error"
            upload.error_message = "File format not recognized as GARBE Mieterliste CSV"
            db.commit()
            return

        result = parser.parse(file_content)
        schema_warnings = validate_schema(result.metadata)
        all_warnings = result.warnings + schema_warnings

        upload.stichtag = result.metadata.stichtag
        upload.fund_label = result.metadata.fund_label
        upload.column_fingerprint = result.metadata.column_fingerprint
        upload.column_headers_json = result.metadata.column_headers
        upload.parser_warnings_json = all_warnings
        upload.row_count = result.stats.get("total_rows", 0)
        upload.data_row_count = result.stats.get("data_rows", 0)
        upload.summary_row_count = result.stats.get("summary_rows", 0)
        upload.orphan_row_count = result.stats.get("orphan_rows", 0)

        db_rows = []
        for row_dict in result.rows:
            row_type = row_dict.pop("row_type")
            row_number = row_dict.pop("row_number")
            fund_inherited = row_dict.pop("fund_inherited", False)

            db_row = RawRentRoll(
                upload_id=upload_id,
                row_number=row_number,
                row_type=row_type,
                fund_inherited=fund_inherited,
                **row_dict,
            )
            db_rows.append(db_row)

        db.bulk_save_objects(db_rows)

        for w in schema_warnings:
            db.add(DataInconsistency(
                upload_id=upload_id,
                category="schema_drift",
                severity="warning",
                entity_type="upload",
                entity_id=str(upload_id),
                description=w,
                status="open",
            ))

        orphan_warnings = [w for w in result.warnings if "orphan" in w.lower()]
        for w in orphan_warnings:
            db.add(DataInconsistency(
                upload_id=upload_id,
                category="orphan_row",
                severity="info",
                entity_type="row",
                description=w,
                status="open",
            ))

        from app.core.inconsistency_detector import detect_inconsistencies
        detected = detect_inconsistencies(db, upload_id)
        db.add_all(detected)

        upload.status = "complete"
        db.commit()

    except Exception as e:
        db.rollback()
        upload = db.get(CsvUpload, upload_id)
        if upload:
            upload.status = "error"
            upload.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("..", "").replace("/", "_").replace("\\", "_")
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    upload = CsvUpload(filename=safe_name, status="processing")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    background_tasks.add_task(_process_upload, upload.id, content, safe_name)

    return UploadResponse(
        id=upload.id,
        filename=safe_name,
        status="processing",
        message="Upload received, parsing in background",
    )


@router.get("/uploads", response_model=list[UploadListItem])
def list_uploads(db: Session = Depends(get_db)):
    uploads = db.query(CsvUpload).order_by(CsvUpload.upload_date.desc()).all()
    return uploads


@router.get("/uploads/{upload_id}", response_model=UploadDetail)
def get_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    return upload


@router.get("/uploads/{upload_id}/rows")
def get_upload_rows(
    upload_id: int,
    row_type: str | None = None,
    fund: str | None = None,
    property_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")

    query = db.query(RawRentRoll).filter(RawRentRoll.upload_id == upload_id)
    if row_type:
        query = query.filter(RawRentRoll.row_type == row_type)
    if fund:
        query = query.filter(RawRentRoll.fund == fund)
    if property_id:
        query = query.filter(RawRentRoll.property_id == property_id)

    total = query.count()
    rows = query.order_by(RawRentRoll.row_number).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": [
            {
                "id": r.id,
                "row_number": r.row_number,
                "row_type": r.row_type,
                "fund": r.fund,
                "fund_inherited": r.fund_inherited,
                "property_id": r.property_id,
                "property_name": r.property_name,
                "unit_id": r.unit_id,
                "unit_type": r.unit_type,
                "tenant_name": r.tenant_name,
                "area_sqm": float(r.area_sqm) if r.area_sqm is not None else None,
                "annual_net_rent": float(r.annual_net_rent) if r.annual_net_rent is not None else None,
                "monthly_net_rent": float(r.monthly_net_rent) if r.monthly_net_rent is not None else None,
                "market_rent_monthly": float(r.market_rent_monthly) if r.market_rent_monthly is not None else None,
                "lease_start": r.lease_start.isoformat() if r.lease_start else None,
                "lease_end_actual": r.lease_end_actual.isoformat() if r.lease_end_actual else None,
            }
            for r in rows
        ],
    }


@router.delete("/uploads/{upload_id}")
def delete_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    db.delete(upload)
    db.commit()
    return {"message": "Upload deleted"}

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command 'git diff --name-only' in C:\projects\RentRoll
 succeeded in 281ms:
CLAUDE.md
backend/app/main.py
backend/app/models/schemas.py
backend/test.db
frontend/src/app/globals.css
frontend/src/app/layout.tsx
frontend/src/lib/api.ts
warning: in the working copy of 'CLAUDE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/app/main.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/app/models/schemas.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/uploads/test.csv', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/app/globals.css', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/app/layout.tsx', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/src/lib/api.ts', LF will be replaced by CRLF the next time Git touches it

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Get-ChildItem -Recurse frontend/src -Include *.tsx,*.ts | Select-String -Pattern \"React\\.ReactNode|ReactNode\" | Select-Object Path,LineNumber,Line" in C:\projects\RentRoll
 succeeded in 317ms:

Path                                                       LineNumber Line                                             
----                                                       ---------- ----                                             
C:\projects\RentRoll\frontend\src\app\master-data\page.tsx        853   renderRow: (row: T, index: number) => React....
C:\projects\RentRoll\frontend\src\app\master-data\page.tsx        913   children: React.ReactNode;                     
C:\projects\RentRoll\frontend\src\app\master-data\page.tsx        930   children: React.ReactNode;                     
C:\projects\RentRoll\frontend\src\app\layout.tsx                   19   children: React.ReactNode;                     



exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('backend/app/api/master_data.py')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 155 <= i <= 185:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 343ms:
 155:         .offset(offset)
 156:         .limit(limit)
 157:         .all()
 158:     )
 159: 
 160: 
 161: @router.post("/master-data/tenants", response_model=TenantMasterResponse)
 162: def create_tenant(body: TenantMasterCreate, db: Session = Depends(get_db)):
 163:     data = body.model_dump(exclude={"initial_alias"})
 164:     tenant = TenantMaster(**data)
 165:     db.add(tenant)
 166:     db.flush()
 167:     log_creation(db, "tenant_master", tenant.id, snapshot(tenant, TENANT_FIELDS))
 168: 
 169:     if body.initial_alias:
 170:         alias = TenantNameAlias(
 171:             tenant_master_id=tenant.id,
 172:             csv_tenant_name=body.initial_alias,
 173:         )
 174:         db.add(alias)
 175:         _resolve_inconsistencies(db, "unmapped_tenant", body.initial_alias)
 176: 
 177:     db.commit()
 178:     db.refresh(tenant)
 179:     return tenant
 180: 
 181: 
 182: @router.get("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
 183: def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
 184:     tenant = (
 185:         db.query(TenantMaster)

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('backend/app/api/master_data.py')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 190 <= i <= 210:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 342ms:
 190:     if not tenant:
 191:         raise HTTPException(404, "Tenant not found")
 192:     return tenant
 193: 
 194: 
 195: @router.patch("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
 196: def update_tenant(tenant_id: int, body: TenantMasterUpdate, db: Session = Depends(get_db)):
 197:     tenant = db.get(TenantMaster, tenant_id)
 198:     if not tenant:
 199:         raise HTTPException(404, "Tenant not found")
 200: 
 201:     old = snapshot(tenant, TENANT_FIELDS)
 202:     updates = body.model_dump(exclude_unset=True)
 203:     for field, val in updates.items():
 204:         setattr(tenant, field, val)
 205:     log_changes(db, "tenant_master", tenant.id, old, updates)
 206:     db.commit()
 207:     db.refresh(tenant)
 208:     return tenant
 209: 
 210: 

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('frontend/src/app/master-data/page.tsx')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 88 <= i <= 110:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 338ms:
  88:     await createFundMapping({
  89:       csv_fund_name: formName,
  90:       bvi_fund_id: formBviId || undefined,
  91:       description: formDesc || undefined,
  92:     });
  93:     setShowCreate(false);
  94:     resetForm();
  95:     load();
  96:   };
  97: 
  98:   const handleUpdate = async () => {
  99:     if (!editTarget) return;
 100:     await updateFundMapping(editTarget.id, {
 101:       bvi_fund_id: formBviId || undefined,
 102:       description: formDesc || undefined,
 103:     });
 104:     setEditTarget(null);
 105:     resetForm();
 106:     load();
 107:   };
 108: 
 109:   const handleDelete = async (id: number) => {
 110:     if (!confirm("Delete this fund mapping?")) return;

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('frontend/src/app/master-data/page.tsx')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 268 <= i <= 292:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 335ms:
 268:     load();
 269:   }, [load]);
 270: 
 271:   const handleCreate = async () => {
 272:     await createTenant({
 273:       tenant_name_canonical: formName,
 274:       bvi_tenant_id: formBviId || undefined,
 275:       nace_sector: formNace || undefined,
 276:       initial_alias: formAlias || undefined,
 277:     });
 278:     setShowCreate(false);
 279:     resetForm();
 280:     load();
 281:   };
 282: 
 283:   const handleUpdate = async () => {
 284:     if (!editTarget) return;
 285:     await updateTenant(editTarget.id, {
 286:       tenant_name_canonical: formName || undefined,
 287:       bvi_tenant_id: formBviId || undefined,
 288:       nace_sector: formNace || undefined,
 289:     });
 290:     setEditTarget(null);
 291:     resetForm();
 292:     load();

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('frontend/src/app/master-data/page.tsx')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 550 <= i <= 575:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 379ms:
 550:   const [showCreate, setShowCreate] = useState(false);
 551:   const [editTarget, setEditTarget] = useState<PropertyMaster | null>(null);
 552: 
 553:   const [formPropId, setFormPropId] = useState("");
 554:   const [formFund, setFormFund] = useState("");
 555:   const [formCity, setFormCity] = useState("");
 556:   const [formStreet, setFormStreet] = useState("");
 557:   const [formCountry, setFormCountry] = useState("");
 558: 
 559:   const load = useCallback(async () => {
 560:     const [p, u] = await Promise.all([
 561:       listProperties({ search: search || undefined }),
 562:       listUnmapped("property"),
 563:     ]);
 564:     setProperties(p);
 565:     setUnmapped(u);
 566:   }, [search]);
 567: 
 568:   useEffect(() => {
 569:     load();
 570:   }, [load]);
 571: 
 572:   const handleCreate = async () => {
 573:     await createProperty({
 574:       property_id: formPropId,
 575:       fund_csv_name: formFund || undefined,

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('frontend/src/app/master-data/page.tsx')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 578 <= i <= 600:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 306ms:
 578:       country: formCountry || undefined,
 579:     });
 580:     setShowCreate(false);
 581:     resetForm();
 582:     load();
 583:   };
 584: 
 585:   const handleUpdate = async () => {
 586:     if (!editTarget) return;
 587:     await updateProperty(editTarget.id, {
 588:       fund_csv_name: formFund || undefined,
 589:       city: formCity || undefined,
 590:       street: formStreet || undefined,
 591:       country: formCountry || undefined,
 592:     });
 593:     setEditTarget(null);
 594:     resetForm();
 595:     load();
 596:   };
 597: 
 598:   const handleDelete = async (id: number) => {
 599:     if (!confirm("Delete this property?")) return;
 600:     await deleteProperty(id);

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('frontend/src/lib/api.ts')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 150 <= i <= 176:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 348ms:
 150:   if (!res.ok) throw new Error("Failed to fetch funds");
 151:   return res.json();
 152: }
 153: 
 154: export async function createFundMapping(body: {
 155:   csv_fund_name: string;
 156:   bvi_fund_id?: string;
 157:   description?: string;
 158: }): Promise<FundMapping> {
 159:   const res = await fetch(`${API_BASE}/api/master-data/funds`, {
 160:     method: "POST",
 161:     headers: { "Content-Type": "application/json" },
 162:     body: JSON.stringify(body),
 163:   });
 164:   if (!res.ok) {
 165:     const err = await res.json().catch(() => ({ detail: "Create failed" }));
 166:     throw new Error(err.detail || "Create failed");
 167:   }
 168:   return res.json();
 169: }
 170: 
 171: export async function updateFundMapping(
 172:   id: number,
 173:   body: { bvi_fund_id?: string; description?: string }
 174: ): Promise<FundMapping> {
 175:   const res = await fetch(`${API_BASE}/api/master-data/funds/${id}`, {
 176:     method: "PATCH",

exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
from pathlib import Path
p=Path('backend/app/api/master_data.py')
for i,l in enumerate(p.read_text().splitlines(),1):
    if 230 <= i <= 256:
        print(f\"{i:4}: {l}\")
'@ | python -" in C:\projects\RentRoll
 succeeded in 321ms:
 230:     "/master-data/tenants/{tenant_id}/aliases",
 231:     response_model=TenantAliasResponse,
 232: )
 233: def add_alias(tenant_id: int, body: TenantAliasCreate, db: Session = Depends(get_db)):
 234:     tenant = db.get(TenantMaster, tenant_id)
 235:     if not tenant:
 236:         raise HTTPException(404, "Tenant not found")
 237: 
 238:     existing = db.query(TenantNameAlias).filter(
 239:         TenantNameAlias.csv_tenant_name == body.csv_tenant_name
 240:     ).first()
 241:     if existing:
 242:         raise HTTPException(400, f"Alias '{body.csv_tenant_name}' already exists")
 243: 
 244:     alias = TenantNameAlias(
 245:         tenant_master_id=tenant_id,
 246:         csv_tenant_name=body.csv_tenant_name,
 247:         property_id=body.property_id,
 248:     )
 249:     db.add(alias)
 250:     db.flush()
 251:     _resolve_inconsistencies(db, "unmapped_tenant", body.csv_tenant_name)
 252:     db.commit()
 253:     db.refresh(alias)
 254:     return alias
 255: 
 256: 

codex
The master-data feature is mostly implemented, but there are correctness gaps around tenant alias uniqueness, duplicate unique-key handling, and edit-form update semantics that can lead to wrong mappings or failed updates. These should be addressed before considering the patch correct.

Full review comments:

- [P1] Reject duplicate initial aliases when creating tenants — C:\projects\RentRoll\backend\app\api\master_data.py:169-173
  `create_tenant` inserts `initial_alias` directly without the duplicate check used in `add_alias`, so two tenants can be created with the same `csv_tenant_name`. This creates ambiguous tenant mapping (the detector later resolves by `.first()`), which can silently map uploads to the wrong tenant record; the same alias uniqueness rule should be enforced here before inserting.

- [P2] Return 400 on duplicate BVI tenant IDs — C:\projects\RentRoll\backend\app\api\master_data.py:206-206
  `TenantMaster.bvi_tenant_id` is unique at the DB level, but this update path commits without pre-validation or `IntegrityError` handling. If a user sets a BVI ID that already exists, the request fails as an unhandled 500 instead of a client error, so callers get a server failure for a normal validation case.

- [P2] Preserve field clearing in master-data edit forms — C:\projects\RentRoll\frontend\src\app\master-data\page.tsx:101-102
  The edit handlers coerce blank inputs to `undefined` (`value || undefined`), and `JSON.stringify` drops `undefined` keys, so clearing a previously populated optional field sends no change and the old value stays in the database. This affects fund/tenant/property edit flows when users try to remove values (e.g., BVI IDs or descriptions).

- [P3] Audit tenant alias creations — C:\projects\RentRoll\backend\app\api\master_data.py:249-252
  Alias deletions are audited, but alias creations in this endpoint are not, so the audit trail is incomplete for tenant mapping changes. In environments relying on `master_data_audit` for traceability, newly added aliases will be missing from history even though they change matching behavior.
The master-data feature is mostly implemented, but there are correctness gaps around tenant alias uniqueness, duplicate unique-key handling, and edit-form update semantics that can lead to wrong mappings or failed updates. These should be addressed before considering the patch correct.

Full review comments:

- [P1] Reject duplicate initial aliases when creating tenants — C:\projects\RentRoll\backend\app\api\master_data.py:169-173
  `create_tenant` inserts `initial_alias` directly without the duplicate check used in `add_alias`, so two tenants can be created with the same `csv_tenant_name`. This creates ambiguous tenant mapping (the detector later resolves by `.first()`), which can silently map uploads to the wrong tenant record; the same alias uniqueness rule should be enforced here before inserting.

- [P2] Return 400 on duplicate BVI tenant IDs — C:\projects\RentRoll\backend\app\api\master_data.py:206-206
  `TenantMaster.bvi_tenant_id` is unique at the DB level, but this update path commits without pre-validation or `IntegrityError` handling. If a user sets a BVI ID that already exists, the request fails as an unhandled 500 instead of a client error, so callers get a server failure for a normal validation case.

- [P2] Preserve field clearing in master-data edit forms — C:\projects\RentRoll\frontend\src\app\master-data\page.tsx:101-102
  The edit handlers coerce blank inputs to `undefined` (`value || undefined`), and `JSON.stringify` drops `undefined` keys, so clearing a previously populated optional field sends no change and the old value stays in the database. This affects fund/tenant/property edit flows when users try to remove values (e.g., BVI IDs or descriptions).

- [P3] Audit tenant alias creations — C:\projects\RentRoll\backend\app\api\master_data.py:249-252
  Alias deletions are audited, but alias creations in this endpoint are not, so the audit trail is incomplete for tenant mapping changes. In environments relying on `master_data_audit` for traceability, newly added aliases will be missing from history even though they change matching behavior.
