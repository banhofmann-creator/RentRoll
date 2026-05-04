"use client";

import { useEffect, useState } from "react";
import {
  type UploadListItem,
  getAvailableFunds,
  getAvailableProperties,
  getFundSummaryUrl,
  getLeaseExpiryUrl,
  getPortfolioOverviewUrl,
  getPropertyFactsheetUrl,
  listUploads,
} from "@/lib/api";

function DownloadCard({
  title,
  description,
  onClick,
  disabled,
}: {
  title: string;
  description: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="bg-white rounded-lg border border-garbe-neutral p-5 text-left hover:border-garbe-blau hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <h3 className="font-semibold text-garbe-blau mb-1">{title}</h3>
      <p className="text-sm text-garbe-grau">{description}</p>
    </button>
  );
}

export default function ReportsPage() {
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<number | null>(null);
  const [funds, setFunds] = useState<string[]>([]);
  const [properties, setProperties] = useState<string[]>([]);
  const [selectedFund, setSelectedFund] = useState("");
  const [selectedProperty, setSelectedProperty] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listUploads()
      .then((list) => {
        const complete = list.filter((u) => u.status === "complete");
        setUploads(complete);
        if (complete.length > 0) setSelectedUpload(complete[0].id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedUpload) {
      setFunds([]);
      setProperties([]);
      return;
    }
    Promise.all([
      getAvailableFunds(selectedUpload),
      getAvailableProperties(selectedUpload),
    ]).then(([f, p]) => {
      setFunds(f);
      setProperties(p);
      setSelectedFund(f[0] || "");
      setSelectedProperty(p[0] || "");
    }).catch(() => {});
  }, [selectedUpload]);

  const download = (url: string) => {
    window.open(url, "_blank");
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10">
        <p className="text-garbe-grau">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-garbe-blau mb-2">Reports</h1>
      <p className="text-garbe-grau mb-6">
        Generate PPTX slide decks from your rent roll data.
      </p>

      {uploads.length === 0 ? (
        <div className="bg-garbe-blau-5 rounded-lg p-8 text-center">
          <p className="text-garbe-grau">
            No completed uploads found. Upload a CSV file first.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-8">
            <label className="block text-sm font-medium text-garbe-blau mb-1">
              Select Upload
            </label>
            <select
              value={selectedUpload ?? ""}
              onChange={(e) => setSelectedUpload(Number(e.target.value))}
              className="border border-garbe-neutral rounded px-3 py-2 text-sm w-full max-w-md"
            >
              {uploads.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.filename}
                  {u.stichtag ? ` (${u.stichtag})` : ""} — {u.row_count} rows
                </option>
              ))}
            </select>
          </div>

          <section className="mb-8">
            <h2 className="text-lg font-semibold text-garbe-blau mb-3">
              Portfolio Reports
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <DownloadCard
                title="Portfolio Overview"
                description="KPIs, fund breakdown, top tenants, and full property table."
                onClick={() =>
                  download(getPortfolioOverviewUrl(selectedUpload!))
                }
                disabled={!selectedUpload}
              />
              <DownloadCard
                title="Lease Expiry Profile"
                description="Waterfall chart of lease expirations by year with rent amounts."
                onClick={() => download(getLeaseExpiryUrl(selectedUpload!))}
                disabled={!selectedUpload}
              />
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-lg font-semibold text-garbe-blau mb-3">
              Fund Summary
            </h2>
            <div className="flex flex-wrap items-end gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-garbe-grau mb-1">
                  Fund
                </label>
                <select
                  value={selectedFund}
                  onChange={(e) => setSelectedFund(e.target.value)}
                  className="border border-garbe-neutral rounded px-3 py-2 text-sm min-w-[200px]"
                >
                  {funds.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={() =>
                  download(getFundSummaryUrl(selectedUpload!, selectedFund))
                }
                disabled={!selectedUpload || !selectedFund}
                className="bg-garbe-blau text-white px-4 py-2 rounded text-sm hover:bg-garbe-blau/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Download Fund Summary
              </button>
            </div>
            {funds.length === 0 && (
              <p className="text-sm text-garbe-grau">
                No funds found in this upload.
              </p>
            )}
          </section>

          <section className="mb-8">
            <h2 className="text-lg font-semibold text-garbe-blau mb-3">
              Property Factsheet
            </h2>
            <div className="flex flex-wrap items-end gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-garbe-grau mb-1">
                  Property
                </label>
                <select
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="border border-garbe-neutral rounded px-3 py-2 text-sm min-w-[200px]"
                >
                  {properties.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={() =>
                  download(
                    getPropertyFactsheetUrl(selectedUpload!, selectedProperty)
                  )
                }
                disabled={!selectedUpload || !selectedProperty}
                className="bg-garbe-blau text-white px-4 py-2 rounded text-sm hover:bg-garbe-blau/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Download Factsheet
              </button>
            </div>
            {properties.length === 0 && (
              <p className="text-sm text-garbe-grau">
                No properties found in this upload.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
