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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Browse Data</h1>

      {completedUploads.length === 0 ? (
        <p className="text-gray-500">
          No completed uploads yet. Upload a CSV first.
        </p>
      ) : (
        <>
          <div className="flex gap-4 mb-6 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Upload
              </label>
              <select
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Row type
              </label>
              <select
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
            <p className="text-sm text-gray-500 mb-4">
              Stichtag: {detail.stichtag} | Fund: {detail.fund_label} |{" "}
              Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}{" "}
              rows
            </p>
          )}

          {rows.length > 0 && (
            <>
              <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
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
                          className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {rows.map((r) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-gray-50 ${
                          r.fund_inherited ? "bg-amber-50" : ""
                        }`}
                      >
                        <td className="px-3 py-2 text-gray-500">
                          {r.row_number}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              r.row_type === "data"
                                ? "bg-blue-100 text-blue-700"
                                : r.row_type === "property_summary"
                                  ? "bg-purple-100 text-purple-700"
                                  : r.row_type === "orphan"
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {r.row_type}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-gray-900">{r.fund}</td>
                        <td className="px-3 py-2 text-gray-700">
                          {r.property_id}
                        </td>
                        <td className="px-3 py-2 text-gray-700 max-w-[200px] truncate">
                          {r.property_name}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{r.unit_id}</td>
                        <td className="px-3 py-2 text-gray-600">
                          {r.unit_type}
                        </td>
                        <td className="px-3 py-2 text-gray-900 max-w-[200px] truncate">
                          {r.tenant_name}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {r.area_sqm?.toLocaleString()}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {r.annual_net_rent?.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between items-center mt-4">
                <button
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Previous
                </button>
                <span className="text-sm text-gray-500">
                  Page {Math.floor(offset / limit) + 1} of{" "}
                  {Math.ceil(total / limit)}
                </span>
                <button
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
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
