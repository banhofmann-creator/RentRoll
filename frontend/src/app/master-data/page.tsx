"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  type FundMapping,
  type TenantMaster,
  type PropertyMaster,
  type UnmappedItem,
  type CompletenessResponse,
  type FuzzyMatch,
  type BviImportPreview,
  type BviImportResult,
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
  getCompleteness,
  suggestTenants,
  suggestFunds,
  previewBviImport,
  executeBviImport,
  type ExcelDiff,
  type ExcelApplyResult,
  exportPropertiesUrl,
  previewExcelImport,
  applyExcelImport,
} from "@/lib/api";

type Tab = "funds" | "tenants" | "properties";

export default function MasterDataPage() {
  const [activeTab, setActiveTab] = useState<Tab>("funds");
  const [showCompleteness, setShowCompleteness] = useState(false);
  const [showBviImport, setShowBviImport] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Master Data</h1>
        <div className="flex gap-2">
          <button
            className={`px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${
              showCompleteness
                ? "bg-garbe-blau text-white"
                : "border border-garbe-blau text-garbe-blau hover:bg-garbe-blau hover:text-white"
            }`}
            onClick={() => setShowCompleteness(!showCompleteness)}
          >
            Completeness
          </button>
          <button
            className="px-3 py-1.5 text-sm font-semibold rounded-lg border border-garbe-grun text-garbe-grun hover:bg-garbe-grun hover:text-white transition-colors"
            onClick={() => setShowBviImport(true)}
          >
            Import BVI
          </button>
        </div>
      </div>

      {showCompleteness && <CompletenessDashboard />}

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

      {showBviImport && (
        <BviImportModal onClose={() => setShowBviImport(false)} />
      )}
    </div>
  );
}

// ── Completeness Dashboard ──────────────────────────────────────────

const GROUP_LABELS: Record<string, string> = {
  core_location: "Core / Location",
  green_building: "Green Building",
  financial_valuation: "Financial / Valuation",
  esg_sustainability: "ESG / Sustainability",
  technical_specs: "Technical Specs",
};

function CompletenessDashboard() {
  const [data, setData] = useState<CompletenessResponse | null>(null);

  useEffect(() => {
    getCompleteness().then(setData).catch(() => {});
  }, []);

  if (!data) return null;

  const groupAvg = (group: Record<string, { fill_rate: number }>) => {
    const vals = Object.values(group);
    if (vals.length === 0) return 0;
    return vals.reduce((s, v) => s + v.fill_rate, 0) / vals.length;
  };

  const barColor = (rate: number) =>
    rate >= 0.8
      ? "bg-garbe-grun"
      : rate >= 0.4
        ? "bg-garbe-ocker"
        : "bg-garbe-rot";

  return (
    <div className="mb-6 border border-garbe-neutral rounded-lg bg-white p-4">
      <h3 className="text-sm font-semibold text-garbe-blau uppercase tracking-wider mb-3">
        Property Field Completeness
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(data.property_groups).map(([key, group]) => {
          const avg = groupAvg(group.fields);
          return (
            <div key={key} className="rounded-lg border border-garbe-neutral p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-semibold text-garbe-blau">
                  {GROUP_LABELS[key] || key}
                </span>
                <span className="text-xs text-garbe-blau-60">
                  {Math.round(avg * 100)}%
                </span>
              </div>
              <div className="w-full h-2 bg-garbe-neutral rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${barColor(avg)}`}
                  style={{ width: `${Math.round(avg * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {Object.keys(data.tenant_fields).length > 0 && (
        <>
          <h3 className="text-sm font-semibold text-garbe-blau uppercase tracking-wider mt-4 mb-3">
            Tenant Field Completeness
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(data.tenant_fields).map(([field, stat]) => (
              <div key={field} className="rounded-lg border border-garbe-neutral p-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-semibold text-garbe-blau">
                    {field.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-garbe-blau-60">
                    {stat.filled}/{stat.total}
                  </span>
                </div>
                <div className="w-full h-2 bg-garbe-neutral rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${barColor(stat.fill_rate)}`}
                    style={{ width: `${Math.round(stat.fill_rate * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── BVI Import Modal ───────────────────────────────────────────────

function BviImportModal({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<BviImportPreview | null>(null);
  const [result, setResult] = useState<BviImportResult | null>(null);
  const [mode, setMode] = useState<"fill_gaps" | "overwrite">("fill_gaps");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileSelect = async (f: File) => {
    setFile(f);
    setError("");
    setPreview(null);
    setResult(null);
    setLoading(true);
    try {
      const p = await previewBviImport(f);
      setPreview(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const r = await executeBviImport(file, mode);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Import BVI File" onClose={onClose}>
      {!result ? (
        <>
          <div className="mb-4">
            <label className="block text-sm font-semibold text-garbe-blau mb-2 uppercase tracking-wider">
              BVI XLSX File
            </label>
            <input
              type="file"
              accept=".xlsx"
              className="form-input w-full text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelect(f);
              }}
            />
          </div>

          {loading && (
            <p className="text-sm text-garbe-blau-60 mb-4">Processing...</p>
          )}

          {error && (
            <p className="text-sm text-garbe-rot mb-4">{error}</p>
          )}

          {preview && (
            <div className="mb-4 space-y-3">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg border border-garbe-neutral p-3">
                  <div className="text-2xl font-bold text-garbe-blau">
                    {preview.properties_found}
                  </div>
                  <div className="text-xs text-garbe-blau-60">Properties</div>
                </div>
                <div className="rounded-lg border border-garbe-grun/30 bg-garbe-grun/5 p-3">
                  <div className="text-2xl font-bold text-garbe-grun">
                    {preview.new_properties.length}
                  </div>
                  <div className="text-xs text-garbe-blau-60">New</div>
                </div>
                <div className="rounded-lg border border-garbe-ocker/30 bg-garbe-ocker/5 p-3">
                  <div className="text-2xl font-bold text-garbe-ocker">
                    {preview.existing_properties.length}
                  </div>
                  <div className="text-xs text-garbe-blau-60">Existing</div>
                </div>
              </div>

              {preview.bvi_fund_ids.length > 0 && (
                <div className="text-xs text-garbe-blau-60">
                  Funds: {preview.bvi_fund_ids.join(", ")}
                </div>
              )}

              {preview.warnings.length > 0 && (
                <div className="text-xs text-garbe-ocker">
                  {preview.warnings.length} warning(s)
                </div>
              )}

              <div>
                <label className="block text-sm font-semibold text-garbe-blau mb-2 uppercase tracking-wider">
                  Import Mode
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-garbe-blau cursor-pointer">
                    <input
                      type="radio"
                      checked={mode === "fill_gaps"}
                      onChange={() => setMode("fill_gaps")}
                    />
                    Fill gaps only
                  </label>
                  <label className="flex items-center gap-2 text-sm text-garbe-blau cursor-pointer">
                    <input
                      type="radio"
                      checked={mode === "overwrite"}
                      onChange={() => setMode("overwrite")}
                    />
                    Overwrite existing
                  </label>
                </div>
              </div>
            </div>
          )}

          <ModalActions
            onCancel={onClose}
            onConfirm={handleExecute}
            disabled={!preview || loading}
          />
        </>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 text-center mb-4">
            <div className="rounded-lg border border-garbe-grun/30 bg-garbe-grun/5 p-3">
              <div className="text-2xl font-bold text-garbe-grun">
                {result.created}
              </div>
              <div className="text-xs text-garbe-blau-60">Created</div>
            </div>
            <div className="rounded-lg border border-garbe-ocker/30 bg-garbe-ocker/5 p-3">
              <div className="text-2xl font-bold text-garbe-ocker">
                {result.updated}
              </div>
              <div className="text-xs text-garbe-blau-60">Updated</div>
            </div>
            <div className="rounded-lg border border-garbe-neutral p-3">
              <div className="text-2xl font-bold text-garbe-blau-60">
                {result.skipped}
              </div>
              <div className="text-xs text-garbe-blau-60">Skipped</div>
            </div>
          </div>

          {result.warnings.length > 0 && (
            <div className="text-xs text-garbe-ocker mb-4">
              {result.warnings.length} warning(s) during import
            </div>
          )}

          <div className="flex justify-end">
            <button
              className="px-4 py-2 text-sm font-semibold bg-garbe-blau text-white rounded-lg hover:bg-garbe-blau-80 transition-colors"
              onClick={onClose}
            >
              Done
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

// ── Funds Tab ───────────────────────────────────────────────────────

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
      bvi_fund_id: formBviId || null,
      description: formDesc || null,
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
              {f.bvi_fund_id || "—"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-60">
              {f.description || "—"}
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

// ── Tenants Tab ─────────────────────────────────────────────────────

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
      bvi_tenant_id: formBviId || null,
      nace_sector: formNace || null,
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

  const [suggestions, setSuggestions] = useState<FuzzyMatch[]>([]);
  const suggestTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const openCreate = (prefillAlias?: string) => {
    resetForm();
    setSuggestions([]);
    if (prefillAlias) {
      setFormName(prefillAlias);
      setFormAlias(prefillAlias);
      suggestTenants(prefillAlias).then(setSuggestions).catch(() => {});
    }
    setShowCreate(true);
  };

  const handleNameChange = (val: string) => {
    setFormName(val);
    if (suggestTimer.current) clearTimeout(suggestTimer.current);
    if (val.length >= 2) {
      suggestTimer.current = setTimeout(() => {
        suggestTenants(val).then(setSuggestions).catch(() => {});
      }, 300);
    } else {
      setSuggestions([]);
    }
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
            {tenants.flatMap((t, i) => [
                <tr
                  key={`tenant-${t.id}`}
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
                    {t.bvi_tenant_id || "—"}
                  </td>
                  <td className="px-3 py-2 text-garbe-blau-60">
                    {t.nace_sector || "—"}
                  </td>
                  <td className="px-3 py-2 text-garbe-blau-60">
                    {t.aliases.length > 0
                      ? `${t.aliases.length} alias${t.aliases.length > 1 ? "es" : ""}`
                      : "—"}
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
                </tr>,
                ...(expandedId === t.id
                  ? [<tr key={`tenant-aliases-${t.id}`}>
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
                  </tr>]
                  : []),
            ])}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="Add Tenant" onClose={() => setShowCreate(false)}>
          {suggestions.length > 0 && (
            <div className="mb-3 rounded-lg border border-garbe-ocker/30 bg-garbe-ocker/5 p-3">
              <div className="text-xs font-semibold text-garbe-ocker uppercase tracking-wider mb-2">
                Similar existing tenants
              </div>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <span
                    key={s.id}
                    className="text-xs px-2 py-1 bg-garbe-ocker/20 text-garbe-ocker rounded"
                  >
                    {s.name} ({Math.round(s.score * 100)}%)
                  </span>
                ))}
              </div>
            </div>
          )}
          <FormField label="Canonical Name">
            <input
              className="form-input"
              value={formName}
              onChange={(e) => handleNameChange(e.target.value)}
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

// ── Properties Tab ──────────────────────────────────────────────────

function PropertiesTab() {
  const [properties, setProperties] = useState<PropertyMaster[]>([]);
  const [unmapped, setUnmapped] = useState<UnmappedItem[]>([]);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<PropertyMaster | null>(null);
  const [showExcelImport, setShowExcelImport] = useState(false);

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
      fund_csv_name: formFund || null,
      city: formCity || null,
      street: formStreet || null,
      country: formCountry || null,
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

      <div className="flex gap-2 mb-4 items-end flex-wrap">
        <SearchInput value={search} onChange={setSearch} />
        <a
          href={exportPropertiesUrl()}
          className="px-3 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors whitespace-nowrap"
        >
          Download XLSX
        </a>
        <button
          className="px-3 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors whitespace-nowrap"
          onClick={() => setShowExcelImport(true)}
        >
          Upload &amp; Diff
        </button>
        <Link
          href="/master-data/properties/grid"
          className="px-3 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors whitespace-nowrap"
        >
          Grid Editor
        </Link>
        <button
          className="px-3 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors whitespace-nowrap"
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
              <Link
                href={`/master-data/properties/${p.id}`}
                className="hover:underline"
              >
                {p.property_id}
              </Link>
            </td>
            <td className="px-3 py-2 text-garbe-blau-80">
              {p.fund_csv_name || "—"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-80">{p.city || "—"}</td>
            <td className="px-3 py-2 text-garbe-blau-60 max-w-[200px] truncate">
              {p.street || "—"}
            </td>
            <td className="px-3 py-2 text-garbe-blau-60">
              {p.country || "—"}
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

      {showExcelImport && (
        <ExcelImportModal
          onClose={() => {
            setShowExcelImport(false);
            load();
          }}
        />
      )}
    </>
  );
}

// ── Excel Import Modal ─────────────────────────────────────────────

function ExcelImportModal({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [diffs, setDiffs] = useState<ExcelDiff[] | null>(null);
  const [result, setResult] = useState<ExcelApplyResult | null>(null);
  const [mode, setMode] = useState<"fill_gaps" | "overwrite">("fill_gaps");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileSelect = async (f: File) => {
    setFile(f);
    setError("");
    setDiffs(null);
    setResult(null);
    setLoading(true);
    try {
      const preview = await previewExcelImport(f);
      setDiffs(preview.diffs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const r = await applyExcelImport(file, mode);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Apply failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Upload & Diff Properties" onClose={onClose}>
      {!result ? (
        <>
          <div className="mb-4">
            <label className="block text-sm font-semibold text-garbe-blau mb-2 uppercase tracking-wider">
              XLSX File
            </label>
            <input
              type="file"
              accept=".xlsx"
              className="form-input w-full text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelect(f);
              }}
            />
          </div>

          {loading && <p className="text-sm text-garbe-blau-60 mb-4">Processing...</p>}
          {error && <p className="text-sm text-garbe-rot mb-4">{error}</p>}

          {diffs !== null && (
            <div className="mb-4">
              {diffs.length === 0 ? (
                <p className="text-sm text-garbe-blau-60">No changes detected.</p>
              ) : (
                <>
                  <p className="text-sm text-garbe-blau mb-2">
                    {diffs.length} change(s) detected:
                  </p>
                  <div className="max-h-60 overflow-y-auto border border-garbe-neutral rounded">
                    <table className="min-w-full text-xs">
                      <thead className="bg-garbe-blau-20/40 sticky top-0">
                        <tr>
                          <th className="px-2 py-1 text-left">Property</th>
                          <th className="px-2 py-1 text-left">Field</th>
                          <th className="px-2 py-1 text-left">Current</th>
                          <th className="px-2 py-1 text-left">New</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-garbe-neutral">
                        {diffs.map((d, i) => (
                          <tr
                            key={i}
                            className={
                              d.change_type === "add"
                                ? "bg-garbe-grun/5"
                                : "bg-garbe-ocker/5"
                            }
                          >
                            <td className="px-2 py-1">{d.property_id}</td>
                            <td className="px-2 py-1">{d.field}</td>
                            <td className="px-2 py-1 text-garbe-blau-60">
                              {d.current_value || "—"}
                            </td>
                            <td className="px-2 py-1 font-semibold">
                              {d.new_value}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-3">
                    <label className="block text-sm font-semibold text-garbe-blau mb-2 uppercase tracking-wider">
                      Apply Mode
                    </label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 text-sm text-garbe-blau cursor-pointer">
                        <input
                          type="radio"
                          checked={mode === "fill_gaps"}
                          onChange={() => setMode("fill_gaps")}
                        />
                        Fill gaps only
                      </label>
                      <label className="flex items-center gap-2 text-sm text-garbe-blau cursor-pointer">
                        <input
                          type="radio"
                          checked={mode === "overwrite"}
                          onChange={() => setMode("overwrite")}
                        />
                        Overwrite existing
                      </label>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          <ModalActions
            onCancel={onClose}
            onConfirm={handleApply}
            disabled={!diffs || diffs.length === 0 || loading}
          />
        </>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 text-center mb-4">
            <div className="rounded-lg border border-garbe-grun/30 bg-garbe-grun/5 p-3">
              <div className="text-2xl font-bold text-garbe-grun">{result.created}</div>
              <div className="text-xs text-garbe-blau-60">Created</div>
            </div>
            <div className="rounded-lg border border-garbe-ocker/30 bg-garbe-ocker/5 p-3">
              <div className="text-2xl font-bold text-garbe-ocker">{result.updated}</div>
              <div className="text-xs text-garbe-blau-60">Updated</div>
            </div>
            <div className="rounded-lg border border-garbe-neutral p-3">
              <div className="text-2xl font-bold text-garbe-blau-60">{result.skipped}</div>
              <div className="text-xs text-garbe-blau-60">Skipped</div>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              className="px-4 py-2 text-sm font-semibold bg-garbe-blau text-white rounded-lg hover:bg-garbe-blau-80 transition-colors"
              onClick={onClose}
            >
              Done
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

// ── Shared Components ───────────────────────────────────────────────

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
