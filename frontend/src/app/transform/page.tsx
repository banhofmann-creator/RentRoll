"use client";

import { useEffect, useState } from "react";
import {
  type G2Row,
  type UploadListItem,
  type ValidationIssue,
  type Z1Row,
  getG2Preview,
  getValidation,
  getZ1Preview,
  listUploads,
} from "@/lib/api";

type Tab = "z1" | "g2" | "validation";

export default function TransformPage() {
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("z1");

  const [z1Rows, setZ1Rows] = useState<Z1Row[]>([]);
  const [g2Rows, setG2Rows] = useState<G2Row[]>([]);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>(
    []
  );
  const [propsChecked, setPropsChecked] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listUploads()
      .then((u) => {
        const complete = u.filter((x) => x.status === "complete");
        setUploads(complete);
        if (complete.length > 0) setSelectedUpload(complete[0].id);
      })
      .catch(() => setError("Failed to load uploads"));
  }, []);

  useEffect(() => {
    if (!selectedUpload) return;
    setLoading(true);
    setError("");
    setZ1Rows([]);
    setG2Rows([]);
    setValidationIssues([]);

    const load = async () => {
      try {
        const [z1, g2, val] = await Promise.all([
          getZ1Preview(selectedUpload),
          getG2Preview(selectedUpload),
          getValidation(selectedUpload),
        ]);
        setZ1Rows(z1.rows);
        setG2Rows(g2.rows);
        setValidationIssues(val.issues);
        setPropsChecked(val.properties_checked);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load preview");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [selectedUpload]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-garbe-blau mb-6">
        Transform Preview
      </h1>

      <div className="flex items-center gap-4 mb-6">
        <label className="text-sm font-semibold text-garbe-blau">Upload:</label>
        <select
          className="form-input text-sm"
          value={selectedUpload ?? ""}
          onChange={(e) => setSelectedUpload(Number(e.target.value))}
        >
          {uploads.map((u) => (
            <option key={u.id} value={u.id}>
              {u.filename} ({u.stichtag || "no date"}) — {u.row_count} rows
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-garbe-rot text-sm mb-4">{error}</p>}

      <div className="flex gap-1 mb-4">
        {(
          [
            ["z1", `Z1 Tenants & Leases (${z1Rows.length})`],
            ["g2", `G2 Property Data (${g2Rows.length})`],
            [
              "validation",
              `Validation ${validationIssues.length > 0 ? `(${validationIssues.length} issues)` : "(clean)"}`,
            ],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors ${
              tab === key
                ? "bg-garbe-blau text-white"
                : "bg-garbe-blau-20/40 text-garbe-blau hover:bg-garbe-blau-20"
            }`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-garbe-blau-60 text-sm py-8">Loading preview...</p>
      ) : (
        <div className="bg-white border border-garbe-neutral rounded-lg overflow-hidden">
          {tab === "z1" && <Z1Table rows={z1Rows} />}
          {tab === "g2" && <G2Table rows={g2Rows} />}
          {tab === "validation" && (
            <ValidationPanel
              issues={validationIssues}
              propsChecked={propsChecked}
            />
          )}
        </div>
      )}
    </div>
  );
}

function Z1Table({ rows }: { rows: Z1Row[] }) {
  if (rows.length === 0)
    return <p className="p-6 text-garbe-blau-60 text-sm">No Z1 rows.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-garbe-blau text-white text-left">
            <th className="px-3 py-2">Fund ID</th>
            <th className="px-3 py-2">Period</th>
            <th className="px-3 py-2">Property</th>
            <th className="px-3 py-2">Tenant</th>
            <th className="px-3 py-2">BVI Tenant ID</th>
            <th className="px-3 py-2">NACE Sector</th>
            <th className="px-3 py-2">PD Min</th>
            <th className="px-3 py-2">PD Max</th>
            <th className="px-3 py-2 text-right">Contract Rent</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              className={i % 2 === 0 ? "bg-white" : "bg-garbe-blau-20/20"}
            >
              <td className="px-3 py-1.5">{r.bvi_fund_id ?? "—"}</td>
              <td className="px-3 py-1.5">{r.stichtag ?? "—"}</td>
              <td className="px-3 py-1.5">{r.property_id}</td>
              <td className="px-3 py-1.5 max-w-[200px] truncate">
                {r.tenant_name}
              </td>
              <td className="px-3 py-1.5">{r.bvi_tenant_id ?? "—"}</td>
              <td className="px-3 py-1.5">{r.nace_sector ?? "—"}</td>
              <td className="px-3 py-1.5">
                {r.pd_min != null ? r.pd_min.toFixed(4) : "—"}
              </td>
              <td className="px-3 py-1.5">
                {r.pd_max != null ? r.pd_max.toFixed(4) : "—"}
              </td>
              <td className="px-3 py-1.5 text-right font-mono">
                {r.contractual_rent.toLocaleString("de-DE", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const G2_COLUMN_GROUPS: {
  label: string;
  cols: { key: string; label: string; fmt?: "num" | "pct" | "int" }[];
}[] = [
  {
    label: "Identity",
    cols: [
      { key: "fund_id", label: "Fund" },
      { key: "property_id", label: "Property" },
      { key: "label", label: "Name" },
      { key: "city", label: "City" },
      { key: "country", label: "Country" },
      { key: "use_type_primary", label: "Use Type" },
    ],
  },
  {
    label: "Areas",
    cols: [
      { key: "rentable_area", label: "Rentable", fmt: "num" },
      { key: "floorspace_let", label: "Let Area", fmt: "num" },
      { key: "tenant_count", label: "Tenants", fmt: "int" },
      { key: "parking_total", label: "Parking", fmt: "int" },
      { key: "parking_let", label: "Parking Let", fmt: "int" },
    ],
  },
  {
    label: "Rent",
    cols: [
      { key: "contractual_rent", label: "Contract", fmt: "num" },
      { key: "rent_per_sqm", label: "/sqm", fmt: "num" },
      { key: "market_rental_value", label: "Market", fmt: "num" },
      { key: "reversion", label: "Reversion", fmt: "pct" },
    ],
  },
  {
    label: "Lease Expiry",
    cols: [
      { key: "lease_term_avg", label: "WAULT", fmt: "num" },
    ],
  },
  {
    label: "Valuation",
    cols: [
      { key: "fair_value", label: "Fair Value", fmt: "num" },
      { key: "epc_rating", label: "EPC" },
    ],
  },
];

function G2Table({ rows }: { rows: G2Row[] }) {
  const [groupIdx, setGroupIdx] = useState(0);

  if (rows.length === 0)
    return <p className="p-6 text-garbe-blau-60 text-sm">No G2 rows.</p>;

  const group = G2_COLUMN_GROUPS[groupIdx];

  const fmtVal = (
    val: unknown,
    fmt?: "num" | "pct" | "int"
  ): string => {
    if (val == null) return "—";
    if (fmt === "pct")
      return (Number(val) * 100).toFixed(1) + "%";
    if (fmt === "int") return String(Math.round(Number(val)));
    if (fmt === "num")
      return Number(val).toLocaleString("de-DE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    return String(val);
  };

  return (
    <div>
      <div className="flex gap-1 p-2 border-b border-garbe-neutral bg-garbe-blau-20/20">
        {G2_COLUMN_GROUPS.map((g, i) => (
          <button
            key={g.label}
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
              groupIdx === i
                ? "bg-garbe-blau text-white"
                : "text-garbe-blau hover:bg-garbe-blau-20"
            }`}
            onClick={() => setGroupIdx(i)}
          >
            {g.label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-garbe-blau text-white text-left">
              {group.cols.map((c) => (
                <th
                  key={c.key}
                  className={`px-3 py-2 ${c.fmt ? "text-right" : ""}`}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={i}
                className={i % 2 === 0 ? "bg-white" : "bg-garbe-blau-20/20"}
              >
                {group.cols.map((c) => (
                  <td
                    key={c.key}
                    className={`px-3 py-1.5 ${c.fmt ? "text-right font-mono" : ""}`}
                  >
                    {fmtVal(r[c.key], c.fmt)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ValidationPanel({
  issues,
  propsChecked,
}: {
  issues: ValidationIssue[];
  propsChecked: number;
}) {
  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-4">
        <div
          className={`w-3 h-3 rounded-full ${issues.length === 0 ? "bg-garbe-grun" : "bg-garbe-rot"}`}
        />
        <span className="text-sm font-semibold text-garbe-blau">
          {issues.length === 0
            ? "All checks passed"
            : `${issues.length} issue${issues.length !== 1 ? "s" : ""} found`}
        </span>
        <span className="text-xs text-garbe-blau-60">
          ({propsChecked} properties checked)
        </span>
      </div>

      {issues.length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-garbe-blau text-white text-left">
              <th className="px-3 py-2">Property</th>
              <th className="px-3 py-2">Field</th>
              <th className="px-3 py-2 text-right">Expected</th>
              <th className="px-3 py-2 text-right">Actual</th>
              <th className="px-3 py-2 text-right">Deviation</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((iss, i) => (
              <tr
                key={i}
                className={i % 2 === 0 ? "bg-white" : "bg-garbe-blau-20/20"}
              >
                <td className="px-3 py-1.5">{iss.property_id}</td>
                <td className="px-3 py-1.5">{iss.field}</td>
                <td className="px-3 py-1.5 text-right font-mono">
                  {iss.expected.toLocaleString("de-DE", {
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td className="px-3 py-1.5 text-right font-mono">
                  {iss.actual.toLocaleString("de-DE", {
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td
                  className={`px-3 py-1.5 text-right font-semibold ${iss.deviation_pct > 5 ? "text-garbe-rot" : "text-garbe-ocker"}`}
                >
                  {iss.deviation_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
