"use client";

import { useEffect, useState } from "react";
import {
  type FinalizeCheck,
  type Period,
  type UploadListItem,
  createPeriod,
  deletePeriod,
  finalizePeriod,
  getFinalizeCheck,
  listPeriods,
  listUploads,
  periodExportUrl,
} from "@/lib/api";

type ModalState =
  | { kind: "none" }
  | { kind: "create" }
  | { kind: "finalize-check"; period: Period; check: FinalizeCheck | null; loading: boolean }
  | { kind: "confirm-delete"; period: Period };

export default function PeriodsPage() {
  const [periods, setPeriods] = useState<Period[]>([]);
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<ModalState>({ kind: "none" });
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const refresh = async () => {
    try {
      const [p, u] = await Promise.all([listPeriods(), listUploads()]);
      setPeriods(p);
      setUploads(u.filter((x) => x.status === "complete"));
    } catch {
      setError("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleCreate = async () => {
    if (!selectedUploadId) return;
    setActionLoading(true);
    setError("");
    try {
      await createPeriod(selectedUploadId);
      setModal({ kind: "none" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalizeCheck = async (period: Period) => {
    setModal({ kind: "finalize-check", period, check: null, loading: true });
    try {
      const check = await getFinalizeCheck(period.id);
      setModal({ kind: "finalize-check", period, check, loading: false });
    } catch {
      setError("Failed to run finalization check");
      setModal({ kind: "none" });
    }
  };

  const handleFinalize = async (periodId: number) => {
    setActionLoading(true);
    setError("");
    try {
      await finalizePeriod(periodId);
      setModal({ kind: "none" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Finalize failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (periodId: number) => {
    setActionLoading(true);
    setError("");
    try {
      await deletePeriod(periodId);
      setModal({ kind: "none" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setActionLoading(false);
    }
  };

  const usedUploadIds = new Set(periods.map((p) => p.upload_id));
  const availableUploads = uploads.filter((u) => !usedUploadIds.has(u.id));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-garbe-blau">
          Reporting Periods
        </h1>
        <button
          onClick={() => {
            setSelectedUploadId(availableUploads[0]?.id ?? null);
            setModal({ kind: "create" });
          }}
          disabled={availableUploads.length === 0}
          className="px-4 py-2 bg-garbe-blau text-white text-sm font-medium rounded hover:bg-garbe-blau/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          New Period
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-garbe-rot/10 border border-garbe-rot/30 text-garbe-rot rounded text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-bold">
            ×
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : periods.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No reporting periods yet</p>
          <p className="text-sm">
            Create one from a completed upload to start.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Stichtag
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Upload
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Finalized
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {periods.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {p.stichtag ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    #{p.upload_id}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {p.finalized_at
                      ? new Date(p.finalized_at).toLocaleString("de-DE")
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(p.created_at).toLocaleString("de-DE")}
                  </td>
                  <td className="px-4 py-3 text-sm text-right space-x-2">
                    <a
                      href={periodExportUrl(p.id)}
                      className="text-garbe-blau hover:underline"
                    >
                      Export
                    </a>
                    {p.status === "draft" && (
                      <>
                        <button
                          onClick={() => handleFinalizeCheck(p)}
                          className="text-garbe-grun hover:underline"
                        >
                          Finalize
                        </button>
                        <button
                          onClick={() =>
                            setModal({ kind: "confirm-delete", period: p })
                          }
                          className="text-garbe-rot hover:underline"
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {modal.kind === "create" && (
        <Modal onClose={() => setModal({ kind: "none" })}>
          <h2 className="text-lg font-semibold text-garbe-blau mb-4">
            Create Reporting Period
          </h2>
          {availableUploads.length === 0 ? (
            <p className="text-gray-500 text-sm">
              No available uploads. All completed uploads already have periods.
            </p>
          ) : (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Upload
              </label>
              <select
                value={selectedUploadId ?? ""}
                onChange={(e) => setSelectedUploadId(Number(e.target.value))}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-4"
              >
                {availableUploads.map((u) => (
                  <option key={u.id} value={u.id}>
                    #{u.id} — {u.filename} ({u.stichtag ?? "no date"})
                  </option>
                ))}
              </select>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setModal({ kind: "none" })}
                  className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={actionLoading || !selectedUploadId}
                  className="px-4 py-2 text-sm bg-garbe-blau text-white rounded hover:bg-garbe-blau/90 disabled:opacity-50"
                >
                  {actionLoading ? "Creating…" : "Create Period"}
                </button>
              </div>
            </>
          )}
        </Modal>
      )}

      {/* Finalize Check Modal */}
      {modal.kind === "finalize-check" && (
        <Modal onClose={() => setModal({ kind: "none" })}>
          <h2 className="text-lg font-semibold text-garbe-blau mb-4">
            Finalize Period — {modal.period.stichtag}
          </h2>
          {modal.loading ? (
            <p className="text-gray-500 text-sm">Running checks…</p>
          ) : modal.check ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <CheckRow
                  label="Blocking errors"
                  value={modal.check.blocking_errors}
                  ok={modal.check.blocking_errors === 0}
                />
                <CheckRow
                  label="Unmapped tenants"
                  value={modal.check.unmapped_tenants}
                  ok={modal.check.unmapped_tenants === 0}
                />
                <CheckRow
                  label="Unmapped funds"
                  value={modal.check.unmapped_funds}
                  ok={modal.check.unmapped_funds === 0}
                />
                <CheckRow
                  label="Property completeness"
                  value={`${modal.check.property_completeness_pct}%`}
                  ok={modal.check.property_completeness_pct >= 70}
                />
              </div>

              {modal.check.warnings.length > 0 && (
                <div className="bg-garbe-ocker/10 border border-garbe-ocker/30 rounded p-3">
                  <p className="text-xs font-medium text-garbe-ocker mb-1">
                    Warnings
                  </p>
                  <ul className="text-xs text-gray-700 list-disc list-inside">
                    {modal.check.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setModal({ kind: "none" })}
                  className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleFinalize(modal.period.id)}
                  disabled={actionLoading || !modal.check.can_finalize}
                  className="px-4 py-2 text-sm bg-garbe-grun text-white rounded hover:bg-garbe-grun/90 disabled:opacity-50"
                >
                  {actionLoading
                    ? "Finalizing…"
                    : modal.check.can_finalize
                      ? "Confirm Finalize"
                      : "Cannot Finalize"}
                </button>
              </div>
            </div>
          ) : null}
        </Modal>
      )}

      {/* Delete Confirmation */}
      {modal.kind === "confirm-delete" && (
        <Modal onClose={() => setModal({ kind: "none" })}>
          <h2 className="text-lg font-semibold text-garbe-rot mb-4">
            Delete Period
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Delete the draft period for{" "}
            <strong>{modal.period.stichtag}</strong>? This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setModal({ kind: "none" })}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => handleDelete(modal.period.id)}
              disabled={actionLoading}
              className="px-4 py-2 text-sm bg-garbe-rot text-white rounded hover:bg-garbe-rot/90 disabled:opacity-50"
            >
              {actionLoading ? "Deleting…" : "Delete"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors =
    status === "finalized"
      ? "bg-garbe-grun/10 text-garbe-grun border-garbe-grun/30"
      : "bg-garbe-ocker/10 text-garbe-ocker border-garbe-ocker/30";
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${colors}`}
    >
      {status}
    </span>
  );
}

function CheckRow({
  label,
  value,
  ok,
}: {
  label: string;
  value: number | string;
  ok: boolean;
}) {
  return (
    <>
      <span className="text-gray-600">{label}</span>
      <span className={`font-medium ${ok ? "text-garbe-grun" : "text-garbe-rot"}`}>
        {value}
      </span>
    </>
  );
}

function Modal({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        {children}
      </div>
    </div>
  );
}
