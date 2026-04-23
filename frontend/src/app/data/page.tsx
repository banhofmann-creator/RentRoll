"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type UploadDetail,
  type UploadListItem,
  getUpload,
  getUploadRows,
  listUploads,
} from "@/lib/api";

interface RowData {
  id: number;
  row_number: number;
  row_type: string;
  fund: string | null;
  fund_inherited: boolean;
  property_id: string | null;
  property_name: string | null;
  unit_id: string | null;
  unit_type: string | null;
  tenant_name: string | null;
  area_sqm: number | null;
  annual_net_rent: number | null;
}

export default function DataPage() {
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<number | null>(null);
  const [detail, setDetail] = useState<UploadDetail | null>(null);
  const [rows, setRows] = useState<RowData[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [rowTypeFilter, setRowTypeFilter] = useState<string>("");
  const limit = 50;

  useEffect(() => {
    listUploads().then(setUploads).catch(() => {});
  }, []);

  const loadRows = useCallback(async () => {
    if (!selectedUpload) return;
    try {
      const [d, r] = await Promise.all([
        getUpload(selectedUpload),
        getUploadRows(selectedUpload, {
          row_type: rowTypeFilter || undefined,
          offset,
          limit,
        }),
      ]);
      setDetail(d);
      setRows(r.rows);
      setTotal(r.total);
    } catch {
      // ignore
    }
  }, [selectedUpload, offset, rowTypeFilter]);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const completedUploads = uploads.filter((u) => u.status === "complete");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Browse Data</h1>

      {completedUploads.length === 0 ? (
        <p className="text-garbe-blau-40">
          No completed uploads yet. Upload a CSV first.
        </p>
      ) : (
        <>
          <div className="flex gap-4 mb-6 items-end">
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

            <div>
              <label className="block text-sm font-semibold text-garbe-blau mb-1 uppercase tracking-wider">
                Row type
              </label>
              <select
                className="border border-garbe-neutral rounded-lg px-3 py-2 text-sm bg-white text-garbe-blau focus:border-garbe-blau-60 focus:outline-none"
                value={rowTypeFilter}
                onChange={(e) => {
                  setRowTypeFilter(e.target.value);
                  setOffset(0);
                }}
              >
                <option value="">All</option>
                <option value="data">Data</option>
                <option value="property_summary">Summary</option>
                <option value="orphan">Orphan</option>
                <option value="total">Total</option>
              </select>
            </div>
          </div>

          {detail && (
            <p className="text-sm text-garbe-blau-60 mb-4">
              Stichtag: {detail.stichtag} | Fund: {detail.fund_label} |{" "}
              Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}{" "}
              rows
            </p>
          )}

          {rows.length > 0 && (
            <>
              <div className="bg-white border border-garbe-neutral rounded-lg overflow-x-auto">
                <table className="min-w-full divide-y divide-garbe-neutral text-sm">
                  <thead className="bg-garbe-blau-20/40">
                    <tr>
                      {[
                        "Row",
                        "Type",
                        "Fund",
                        "Prop ID",
                        "Property",
                        "Unit",
                        "Type",
                        "Tenant",
                        "Area (m²)",
                        "Annual Rent",
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
                    {rows.map((r, i) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-garbe-neutral/50 ${
                          r.fund_inherited
                            ? "bg-garbe-ocker/10"
                            : i % 2 === 1
                              ? "bg-garbe-offwhite"
                              : ""
                        }`}
                      >
                        <td className="px-3 py-2 text-garbe-blau-40">
                          {r.row_number}
                        </td>
                        <td className="px-3 py-2">
                          <RowTypeBadge type={r.row_type} />
                        </td>
                        <td className="px-3 py-2 text-garbe-blau">
                          {r.fund}
                        </td>
                        <td className="px-3 py-2 text-garbe-blau-80">
                          {r.property_id}
                        </td>
                        <td className="px-3 py-2 text-garbe-blau-80 max-w-[200px] truncate">
                          {r.property_name}
                        </td>
                        <td className="px-3 py-2 text-garbe-blau-60">
                          {r.unit_id}
                        </td>
                        <td className="px-3 py-2 text-garbe-blau-60">
                          {r.unit_type}
                        </td>
                        <td className="px-3 py-2 text-garbe-blau max-w-[200px] truncate">
                          {r.tenant_name}
                        </td>
                        <td className="px-3 py-2 text-right text-garbe-blau-80">
                          {r.area_sqm?.toLocaleString()}
                        </td>
                        <td className="px-3 py-2 text-right text-garbe-blau-80">
                          {r.annual_net_rent?.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between items-center mt-4">
                <button
                  className="px-4 py-1.5 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Previous
                </button>
                <span className="text-sm text-garbe-blau-60">
                  Page {Math.floor(offset / limit) + 1} of{" "}
                  {Math.ceil(total / limit)}
                </span>
                <button
                  className="px-4 py-1.5 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={offset + limit >= total}
                  onClick={() => setOffset(offset + limit)}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function RowTypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    data: "bg-garbe-blau/10 text-garbe-blau",
    property_summary: "bg-garbe-turkis/10 text-garbe-turkis",
    orphan: "bg-garbe-ocker/15 text-garbe-ocker",
    total: "bg-garbe-neutral text-garbe-blau-60",
  };
  return (
    <span
      className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
        styles[type] || "bg-garbe-neutral text-garbe-blau-60"
      }`}
    >
      {type}
    </span>
  );
}
