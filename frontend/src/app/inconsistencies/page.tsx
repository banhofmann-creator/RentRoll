"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type InconsistencyItem,
  type InconsistencySummary,
  type UploadListItem,
  getInconsistencySummary,
  listInconsistencies,
  listUploads,
  recheckInconsistencies,
  updateInconsistency,
} from "@/lib/api";

const LIMIT = 50;

export default function InconsistenciesPage() {
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<number | null>(null);
  const [summary, setSummary] = useState<InconsistencySummary | null>(null);
  const [items, setItems] = useState<InconsistencyItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [resolveTarget, setResolveTarget] = useState<InconsistencyItem | null>(
    null
  );
  const [resolveNote, setResolveNote] = useState("");
  const [resolveAction, setResolveAction] = useState<string>("resolved");
  const [rechecking, setRechecking] = useState(false);

  useEffect(() => {
    listUploads().then(setUploads).catch(() => {});
  }, []);

  const loadData = useCallback(async () => {
    if (!selectedUpload) return;
    try {
      const [s, list] = await Promise.all([
        getInconsistencySummary(selectedUpload),
        listInconsistencies({
          upload_id: selectedUpload,
          category: categoryFilter || undefined,
          severity: severityFilter || undefined,
          status: statusFilter || undefined,
          offset,
          limit: LIMIT,
        }),
      ]);
      setSummary(s);
      setItems(list);
    } catch {
      // ignore
    }
  }, [selectedUpload, categoryFilter, severityFilter, statusFilter, offset]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleResolve = async () => {
    if (!resolveTarget) return;
    await updateInconsistency(resolveTarget.id, {
      status: resolveAction,
      resolution_note: resolveNote || undefined,
    });
    setResolveTarget(null);
    setResolveNote("");
    loadData();
  };

  const handleRecheck = async () => {
    if (!selectedUpload) return;
    setRechecking(true);
    try {
      await recheckInconsistencies(selectedUpload);
      await loadData();
    } finally {
      setRechecking(false);
    }
  };

  const completedUploads = uploads.filter((u) => u.status === "complete");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Data Quality</h1>

      {completedUploads.length === 0 ? (
        <p className="text-garbe-blau-40">
          No completed uploads yet. Upload a CSV first.
        </p>
      ) : (
        <>
          <div className="flex gap-4 mb-6 items-end flex-wrap">
            <div>
              <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
                Upload
              </label>
              <select
                className="border border-garbe-neutral rounded-lg px-3 py-2 text-sm bg-white text-garbe-blau focus:border-garbe-blau-60 focus:outline-none"
                value={selectedUpload ?? ""}
                onChange={(e) => {
                  setSelectedUpload(
                    e.target.value ? Number(e.target.value) : null
                  );
                  setOffset(0);
                }}
              >
                <option value="">Select an upload...</option>
                {completedUploads.map((u) => (
                  <option key={u.id} value={u.id}>
                    #{u.id} — {u.filename}{" "}
                    {u.stichtag ? `(${u.stichtag})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {selectedUpload && (
              <button
                className="px-4 py-2 text-sm font-semibold bg-garbe-blau text-white rounded-lg hover:bg-garbe-blau-80 transition-colors disabled:opacity-40"
                onClick={handleRecheck}
                disabled={rechecking}
              >
                {rechecking ? "Rechecking..." : "Recheck"}
              </button>
            )}
          </div>

          {summary && selectedUpload && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                <SummaryCard
                  label="Errors"
                  count={summary.by_severity.error ?? 0}
                  color="bg-garbe-rot/10 text-garbe-rot border-garbe-rot/30"
                />
                <SummaryCard
                  label="Warnings"
                  count={summary.by_severity.warning ?? 0}
                  color="bg-garbe-ocker/10 text-garbe-ocker border-garbe-ocker/30"
                />
                <SummaryCard
                  label="Info"
                  count={summary.by_severity.info ?? 0}
                  color="bg-garbe-turkis/10 text-garbe-turkis border-garbe-turkis/30"
                />
                <SummaryCard
                  label="Resolved"
                  count={
                    (summary.by_status.resolved ?? 0) +
                    (summary.by_status.acknowledged ?? 0) +
                    (summary.by_status.ignored ?? 0)
                  }
                  color="bg-garbe-grun/10 text-garbe-grun border-garbe-grun/30"
                />
              </div>

              {/* Export readiness banner */}
              <div
                className={`rounded-lg px-4 py-3 mb-6 text-sm font-semibold ${
                  summary.has_blocking_errors
                    ? "bg-garbe-rot/10 text-garbe-rot border border-garbe-rot/30"
                    : "bg-garbe-grun/10 text-garbe-grun border border-garbe-grun/30"
                }`}
              >
                {summary.has_blocking_errors
                  ? "Export blocked — resolve all errors before exporting"
                  : "Export ready — no blocking errors"}
              </div>

              {/* Filters */}
              <div className="flex gap-4 mb-4 flex-wrap">
                <FilterSelect
                  label="Category"
                  value={categoryFilter}
                  onChange={(v) => {
                    setCategoryFilter(v);
                    setOffset(0);
                  }}
                  options={[
                    ["", "All"],
                    ["aggregation_mismatch", "Aggregation mismatch"],
                    ["unmapped_tenant", "Unmapped tenant"],
                    ["unmapped_fund", "Unmapped fund"],
                    ["missing_metadata", "Missing metadata"],
                    ["orphan_row", "Orphan row"],
                    ["schema_drift", "Schema drift"],
                  ]}
                />
                <FilterSelect
                  label="Severity"
                  value={severityFilter}
                  onChange={(v) => {
                    setSeverityFilter(v);
                    setOffset(0);
                  }}
                  options={[
                    ["", "All"],
                    ["error", "Error"],
                    ["warning", "Warning"],
                    ["info", "Info"],
                  ]}
                />
                <FilterSelect
                  label="Status"
                  value={statusFilter}
                  onChange={(v) => {
                    setStatusFilter(v);
                    setOffset(0);
                  }}
                  options={[
                    ["", "All"],
                    ["open", "Open"],
                    ["resolved", "Resolved"],
                    ["acknowledged", "Acknowledged"],
                    ["ignored", "Ignored"],
                  ]}
                />
              </div>

              {/* Table */}
              {items.length > 0 ? (
                <>
                  <div className="bg-white border border-garbe-neutral rounded-lg overflow-x-auto">
                    <table className="min-w-full divide-y divide-garbe-neutral text-sm">
                      <thead className="bg-garbe-blau-20/40">
                        <tr>
                          {[
                            "Severity",
                            "Category",
                            "Entity",
                            "Description",
                            "Deviation",
                            "Status",
                            "Action",
                          ].map((h) => (
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
                        {items.map((item, i) => (
                          <tr
                            key={item.id}
                            className={`hover:bg-garbe-neutral/50 ${
                              i % 2 === 1 ? "bg-garbe-offwhite" : ""
                            }`}
                          >
                            <td className="px-3 py-2">
                              <SeverityBadge severity={item.severity} />
                            </td>
                            <td className="px-3 py-2">
                              <CategoryBadge category={item.category} />
                            </td>
                            <td className="px-3 py-2 text-garbe-blau-80 max-w-[200px] truncate">
                              {item.entity_id || "—"}
                            </td>
                            <td className="px-3 py-2 text-garbe-blau max-w-[400px]">
                              {item.description}
                            </td>
                            <td className="px-3 py-2 text-right text-garbe-blau-80">
                              {item.deviation_pct != null
                                ? `${item.deviation_pct}%`
                                : "—"}
                            </td>
                            <td className="px-3 py-2">
                              <StatusBadge status={item.status} />
                            </td>
                            <td className="px-3 py-2">
                              {item.status === "open" && (
                                <button
                                  className="text-xs px-2 py-1 font-semibold bg-garbe-grun text-white rounded hover:bg-garbe-grun-80 transition-colors"
                                  onClick={() => {
                                    setResolveTarget(item);
                                    setResolveNote("");
                                    setResolveAction("resolved");
                                  }}
                                >
                                  Resolve
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <div className="flex justify-between items-center mt-4">
                    <button
                      className="px-4 py-1.5 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      disabled={offset === 0}
                      onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                    >
                      Previous
                    </button>
                    <span className="text-sm text-garbe-blau-60">
                      Showing {offset + 1}–{offset + items.length} of{" "}
                      {summary.total}
                    </span>
                    <button
                      className="px-4 py-1.5 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      disabled={offset + LIMIT >= summary.total}
                      onClick={() => setOffset(offset + LIMIT)}
                    >
                      Next
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-garbe-blau-40 text-sm">
                  No inconsistencies match your filters.
                </p>
              )}
            </>
          )}

          {/* Resolution modal */}
          {resolveTarget && (
            <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
                <h3 className="text-lg font-semibold text-garbe-blau mb-2">
                  Resolve Inconsistency
                </h3>
                <p className="text-sm text-garbe-blau-60 mb-4">
                  {resolveTarget.description}
                </p>

                <div className="mb-4">
                  <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
                    Action
                  </label>
                  <select
                    className="border border-garbe-neutral rounded-lg px-3 py-2 text-sm bg-white text-garbe-blau w-full focus:border-garbe-blau-60 focus:outline-none"
                    value={resolveAction}
                    onChange={(e) => setResolveAction(e.target.value)}
                  >
                    <option value="resolved">Resolve</option>
                    <option value="acknowledged">Acknowledge</option>
                    <option value="ignored">Ignore</option>
                  </select>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
                    Note (optional)
                  </label>
                  <textarea
                    className="border border-garbe-neutral rounded-lg px-3 py-2 text-sm bg-white text-garbe-blau w-full h-24 focus:border-garbe-blau-60 focus:outline-none resize-none"
                    value={resolveNote}
                    onChange={(e) => setResolveNote(e.target.value)}
                    placeholder="Add a resolution note..."
                  />
                </div>

                <div className="flex gap-3 justify-end">
                  <button
                    className="px-4 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors"
                    onClick={() => setResolveTarget(null)}
                  >
                    Cancel
                  </button>
                  <button
                    className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors"
                    onClick={handleResolve}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className={`rounded-lg border px-4 py-3 ${color}`}>
      <div className="text-2xl font-semibold">{count}</div>
      <div className="text-xs font-semibold uppercase tracking-wider">
        {label}
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
        {label}
      </label>
      <select
        className="border border-garbe-neutral rounded-lg px-3 py-2 text-sm bg-white text-garbe-blau focus:border-garbe-blau-60 focus:outline-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map(([val, text]) => (
          <option key={val} value={val}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    error: "bg-garbe-rot/10 text-garbe-rot",
    warning: "bg-garbe-ocker/15 text-garbe-ocker",
    info: "bg-garbe-turkis/10 text-garbe-turkis",
  };
  return (
    <span
      className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
        styles[severity] || "bg-garbe-neutral text-garbe-blau-60"
      }`}
    >
      {severity}
    </span>
  );
}

function CategoryBadge({ category }: { category: string }) {
  const labels: Record<string, string> = {
    aggregation_mismatch: "Aggregation",
    unmapped_tenant: "Unmapped tenant",
    unmapped_fund: "Unmapped fund",
    missing_metadata: "Missing metadata",
    orphan_row: "Orphan row",
    schema_drift: "Schema drift",
  };
  return (
    <span className="text-xs px-1.5 py-0.5 rounded font-semibold bg-garbe-blau/10 text-garbe-blau">
      {labels[category] || category}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: "bg-garbe-rot/10 text-garbe-rot",
    resolved: "bg-garbe-grun/10 text-garbe-grun",
    acknowledged: "bg-garbe-turkis/10 text-garbe-turkis",
    ignored: "bg-garbe-neutral text-garbe-blau-40",
  };
  return (
    <span
      className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
        styles[status] || "bg-garbe-neutral text-garbe-blau-60"
      }`}
    >
      {status}
    </span>
  );
}
