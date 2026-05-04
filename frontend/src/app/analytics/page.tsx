"use client";

import { useEffect, useState } from "react";
import {
  type ComparisonResponse,
  type PeriodKPI,
  type PropertySnapshot,
  comparePeriods,
  getPortfolioKPIs,
  getPropertyHistory,
} from "@/lib/api";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const fmt = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("de-DE", { maximumFractionDigits: 2 });

const fmtPct = (v: number | null | undefined) =>
  v == null ? "—" : `${v.toFixed(1)}%`;

const fmtEur = (v: number | null | undefined) =>
  v == null
    ? "—"
    : v.toLocaleString("de-DE", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      });

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-garbe-neutral p-4">
      <div className="text-xs text-garbe-blau-60 uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="text-xl font-semibold text-garbe-blau">{value}</div>
      {sub && <div className="text-xs text-garbe-blau-60 mt-1">{sub}</div>}
    </div>
  );
}

const METRIC_LABELS: Record<string, string> = {
  total_rent: "Total Rent",
  total_area: "Total Area (sqm)",
  vacant_area: "Vacant Area (sqm)",
  vacancy_rate: "Vacancy Rate (%)",
  tenant_count: "Tenants",
  property_count: "Properties",
  fair_value: "Fair Value",
  total_debt: "Total Debt",
  wault_avg: "WAULT (avg)",
};

export default function AnalyticsPage() {
  const [kpis, setKpis] = useState<PeriodKPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [includeDraft, setIncludeDraft] = useState(false);

  const [compPeriodA, setCompPeriodA] = useState<number | "">("");
  const [compPeriodB, setCompPeriodB] = useState<number | "">("");
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [compLoading, setCompLoading] = useState(false);

  const [propId, setPropId] = useState("");
  const [propHistory, setPropHistory] = useState<PropertySnapshot[] | null>(
    null
  );
  const [propLoading, setPropLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError("");
    getPortfolioKPIs(includeDraft ? "all" : "finalized")
      .then(setKpis)
      .catch(() => setError("Failed to load KPIs"))
      .finally(() => setLoading(false));
  }, [includeDraft]);

  const handleCompare = async () => {
    if (compPeriodA === "" || compPeriodB === "") return;
    setCompLoading(true);
    try {
      const data = await comparePeriods(
        compPeriodA as number,
        compPeriodB as number
      );
      setComparison(data);
    } catch {
      setError("Comparison failed");
    } finally {
      setCompLoading(false);
    }
  };

  const handlePropertyLookup = async () => {
    if (!propId.trim()) return;
    setPropLoading(true);
    try {
      const data = await getPropertyHistory(propId.trim());
      setPropHistory(data);
    } catch {
      setError("Property lookup failed");
    } finally {
      setPropLoading(false);
    }
  };

  const latest = kpis.length > 0 ? kpis[kpis.length - 1] : null;

  const chartData = kpis.map((k) => ({
    stichtag: k.stichtag,
    rent: k.total_rent,
    area: k.total_area,
    vacancy: k.vacancy_rate,
    fairValue: k.fair_value,
    tenants: k.tenant_count,
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl">Portfolio Analytics</h1>
        <label className="flex items-center gap-2 text-sm text-garbe-blau-60">
          <input
            type="checkbox"
            checked={includeDraft}
            onChange={(e) => setIncludeDraft(e.target.checked)}
            className="rounded"
          />
          Include draft periods
        </label>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-garbe-rot/10 text-garbe-rot rounded text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-garbe-blau-60 text-sm">Loading...</div>
      ) : kpis.length === 0 ? (
        <div className="text-garbe-blau-60 text-sm">
          No finalized periods found. Finalize a period to see analytics.
        </div>
      ) : (
        <>
          {/* KPI Summary Cards */}
          {latest && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
              <KpiCard
                label="Total Rent"
                value={fmtEur(latest.total_rent)}
                sub={`as of ${latest.stichtag}`}
              />
              <KpiCard
                label="Total Area"
                value={`${fmt(latest.total_area)} sqm`}
              />
              <KpiCard
                label="Vacancy Rate"
                value={fmtPct(latest.vacancy_rate)}
              />
              <KpiCard
                label="Fair Value"
                value={fmtEur(latest.fair_value)}
              />
              <KpiCard
                label="Properties"
                value={String(latest.property_count)}
              />
              <KpiCard
                label="Tenants"
                value={String(latest.tenant_count)}
              />
              <KpiCard
                label="Total Debt"
                value={fmtEur(latest.total_debt)}
              />
              <KpiCard
                label="WAULT"
                value={latest.wault_avg != null ? `${latest.wault_avg} yrs` : "—"}
              />
            </div>
          )}

          {/* Rent Trend Chart */}
          <div className="bg-white rounded-lg border border-garbe-neutral p-6 mb-6">
            <h3 className="text-sm mb-4">Rent & Fair Value Over Time</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ececec" />
                <XAxis dataKey="stichtag" tick={{ fontSize: 12 }} />
                <YAxis
                  yAxisId="rent"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) =>
                    `${(Number(v) / 1000).toFixed(0)}k`
                  }
                />
                <YAxis
                  yAxisId="fv"
                  orientation="right"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) =>
                    `${(Number(v) / 1_000_000).toFixed(0)}M`
                  }
                />
                <Tooltip
                  formatter={(value, name) => [
                    fmtEur(Number(value)),
                    name === "rent" ? "Total Rent" : "Fair Value",
                  ]}
                />
                <Legend />
                <Area
                  yAxisId="rent"
                  type="monotone"
                  dataKey="rent"
                  name="Total Rent"
                  stroke="#003255"
                  fill="#003255"
                  fillOpacity={0.15}
                />
                <Area
                  yAxisId="fv"
                  type="monotone"
                  dataKey="fairValue"
                  name="Fair Value"
                  stroke="#64B42D"
                  fill="#64B42D"
                  fillOpacity={0.1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Vacancy Trend Chart */}
          <div className="bg-white rounded-lg border border-garbe-neutral p-6 mb-6">
            <h3 className="text-sm mb-4">Vacancy Rate Over Time</h3>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ececec" />
                <XAxis dataKey="stichtag" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(2)}%`, "Vacancy Rate"]}
                />
                <Area
                  type="monotone"
                  dataKey="vacancy"
                  name="Vacancy Rate"
                  stroke="#a48113"
                  fill="#a48113"
                  fillOpacity={0.15}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Period Comparison */}
          <div className="bg-white rounded-lg border border-garbe-neutral p-6 mb-6">
            <h3 className="text-sm mb-4">Period Comparison</h3>
            <div className="flex items-end gap-4 mb-4">
              <div>
                <label className="block text-xs text-garbe-blau-60 mb-1">
                  Period A
                </label>
                <select
                  className="form-input"
                  value={compPeriodA}
                  onChange={(e) =>
                    setCompPeriodA(
                      e.target.value ? Number(e.target.value) : ""
                    )
                  }
                >
                  <option value="">Select...</option>
                  {kpis.map((k) => (
                    <option key={k.period_id} value={k.period_id}>
                      {k.stichtag}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-garbe-blau-60 mb-1">
                  Period B
                </label>
                <select
                  className="form-input"
                  value={compPeriodB}
                  onChange={(e) =>
                    setCompPeriodB(
                      e.target.value ? Number(e.target.value) : ""
                    )
                  }
                >
                  <option value="">Select...</option>
                  {kpis.map((k) => (
                    <option key={k.period_id} value={k.period_id}>
                      {k.stichtag}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCompare}
                disabled={
                  compPeriodA === "" || compPeriodB === "" || compLoading
                }
                className="px-4 py-2 bg-garbe-blau text-white rounded text-sm hover:bg-garbe-blau-80 disabled:opacity-50"
              >
                {compLoading ? "Comparing..." : "Compare"}
              </button>
            </div>
            {comparison && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-garbe-neutral">
                      <th className="text-left py-2 pr-4 text-garbe-blau-60 font-medium">
                        Metric
                      </th>
                      <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                        {comparison.period_a}
                      </th>
                      <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                        {comparison.period_b}
                      </th>
                      <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                        Delta
                      </th>
                      <th className="text-right py-2 pl-4 text-garbe-blau-60 font-medium">
                        Delta %
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.metrics.map((m) => (
                      <tr
                        key={m.metric}
                        className="border-b border-garbe-neutral/50"
                      >
                        <td className="py-2 pr-4 font-medium">
                          {METRIC_LABELS[m.metric] || m.metric}
                        </td>
                        <td className="py-2 px-4 text-right tabular-nums">
                          {fmt(m.period_a_value)}
                        </td>
                        <td className="py-2 px-4 text-right tabular-nums">
                          {fmt(m.period_b_value)}
                        </td>
                        <td
                          className={`py-2 px-4 text-right tabular-nums ${
                            m.delta != null && m.delta > 0
                              ? "text-garbe-grun"
                              : m.delta != null && m.delta < 0
                                ? "text-garbe-rot"
                                : ""
                          }`}
                        >
                          {m.delta != null && m.delta > 0 ? "+" : ""}
                          {fmt(m.delta)}
                        </td>
                        <td
                          className={`py-2 pl-4 text-right tabular-nums ${
                            m.delta_pct != null && m.delta_pct > 0
                              ? "text-garbe-grun"
                              : m.delta_pct != null && m.delta_pct < 0
                                ? "text-garbe-rot"
                                : ""
                          }`}
                        >
                          {m.delta_pct != null && m.delta_pct > 0 ? "+" : ""}
                          {fmtPct(m.delta_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Property History */}
          <div className="bg-white rounded-lg border border-garbe-neutral p-6">
            <h3 className="text-sm mb-4">Property History</h3>
            <div className="flex items-end gap-4 mb-4">
              <div>
                <label className="block text-xs text-garbe-blau-60 mb-1">
                  Property ID
                </label>
                <input
                  className="form-input"
                  placeholder="e.g. 7042"
                  value={propId}
                  onChange={(e) => setPropId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handlePropertyLookup()}
                />
              </div>
              <button
                onClick={handlePropertyLookup}
                disabled={!propId.trim() || propLoading}
                className="px-4 py-2 bg-garbe-blau text-white rounded text-sm hover:bg-garbe-blau-80 disabled:opacity-50"
              >
                {propLoading ? "Loading..." : "Look Up"}
              </button>
            </div>
            {propHistory !== null &&
              (propHistory.length === 0 ? (
                <div className="text-sm text-garbe-blau-60">
                  No history found for property {propId}.
                </div>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={propHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ececec" />
                      <XAxis dataKey="stichtag" tick={{ fontSize: 12 }} />
                      <YAxis
                        yAxisId="rent"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) =>
                          `${(Number(v) / 1000).toFixed(0)}k`
                        }
                      />
                      <YAxis
                        yAxisId="vacancy"
                        orientation="right"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) => `${v}%`}
                        domain={[0, "auto"]}
                      />
                      <Tooltip />
                      <Legend />
                      <Bar
                        yAxisId="rent"
                        dataKey="rent"
                        name="Rent"
                        fill="#003255"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        yAxisId="vacancy"
                        dataKey="vacancy_rate"
                        name="Vacancy %"
                        fill="#a48113"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                  <table className="w-full text-sm mt-4">
                    <thead>
                      <tr className="border-b border-garbe-neutral">
                        <th className="text-left py-2 pr-4 text-garbe-blau-60 font-medium">
                          Stichtag
                        </th>
                        <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                          Rent
                        </th>
                        <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                          Area (sqm)
                        </th>
                        <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                          Vacancy
                        </th>
                        <th className="text-right py-2 px-4 text-garbe-blau-60 font-medium">
                          Tenants
                        </th>
                        <th className="text-right py-2 pl-4 text-garbe-blau-60 font-medium">
                          Fair Value
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {propHistory.map((s) => (
                        <tr
                          key={s.stichtag}
                          className="border-b border-garbe-neutral/50"
                        >
                          <td className="py-2 pr-4">{s.stichtag}</td>
                          <td className="py-2 px-4 text-right tabular-nums">
                            {fmtEur(s.rent)}
                          </td>
                          <td className="py-2 px-4 text-right tabular-nums">
                            {fmt(s.area)}
                          </td>
                          <td className="py-2 px-4 text-right tabular-nums">
                            {fmtPct(s.vacancy_rate)}
                          </td>
                          <td className="py-2 px-4 text-right tabular-nums">
                            {s.tenant_count}
                          </td>
                          <td className="py-2 pl-4 text-right tabular-nums">
                            {fmtEur(s.fair_value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ))}
          </div>
        </>
      )}
    </div>
  );
}
