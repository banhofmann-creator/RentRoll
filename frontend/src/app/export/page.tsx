"use client";

import { useEffect, useState } from "react";
import {
  type ChannelInfo,
  type InvestorPackPreview,
  type Period,
  type PushResult,
  getAvailableFunds,
  getExportChannels,
  investorPackUrl,
  listPeriods,
  periodExportUrl,
  previewInvestorPack,
  pushToChannel,
} from "@/lib/api";

function formatPeriodLabel(period: Period): string {
  return `${period.stichtag ?? "No stichtag"} \u2014 ${period.status}`;
}

export default function ExportPage() {
  const [periods, setPeriods] = useState<Period[]>([]);
  const [channels, setChannels] = useState<ChannelInfo[]>([]);
  const [funds, setFunds] = useState<string[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [selectedFund, setSelectedFund] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("");
  const [preview, setPreview] = useState<InvestorPackPreview | null>(null);
  const [pushResult, setPushResult] = useState<PushResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPeriod =
    periods.find((period) => period.id === selectedPeriodId) ?? null;

  const loadFunds = (uploadId: number | null) => {
    if (!uploadId) {
      setFunds([]);
      return;
    }

    getAvailableFunds(uploadId)
      .then((availableFunds) => {
        setFunds(availableFunds);
      })
      .catch(() => {
        setFunds([]);
      });
  };

  useEffect(() => {
    Promise.all([listPeriods(), getExportChannels()])
      .then(([periodList, channelList]) => {
        setPeriods(periodList);
        setChannels(channelList);
        if (periodList.length > 0) {
          setSelectedPeriodId(periodList[0].id);
          loadFunds(periodList[0].upload_id);
        }
        if (channelList.length > 0) {
          setSelectedChannel(channelList[0].name);
        }
      })
      .catch((err: Error) => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const handlePeriodChange = (value: string) => {
    const periodId = Number(value);
    const period = periods.find((item) => item.id === periodId) ?? null;

    setSelectedPeriodId(periodId);
    setPreview(null);
    setPushResult(null);
    setSelectedFund("");
    loadFunds(period?.upload_id ?? null);
  };

  const effectiveFund = selectedFund || undefined;

  const openDownload = () => {
    if (!selectedPeriodId) return;
    const form = document.createElement("form");
    form.method = "POST";
    form.action = investorPackUrl(selectedPeriodId, effectiveFund);
    form.target = "_blank";
    document.body.appendChild(form);
    form.submit();
    form.remove();
  };

  const handlePreview = async () => {
    if (!selectedPeriodId) return;
    setPreviewLoading(true);
    setPushResult(null);
    setError(null);
    try {
      const manifest = await previewInvestorPack(selectedPeriodId, effectiveFund);
      setPreview(manifest);
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handlePush = async () => {
    if (!selectedPeriodId || !selectedChannel) return;
    setPushLoading(true);
    setError(null);
    try {
      const result = await pushToChannel(
        selectedPeriodId,
        selectedChannel,
        effectiveFund
      );
      setPushResult(result);
    } catch (err) {
      setPushResult(null);
      setError(err instanceof Error ? err.message : "Push failed");
    } finally {
      setPushLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-10">
        <p className="text-garbe-grau">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-garbe-blau mb-2">Export</h1>
      <p className="text-garbe-grau mb-8">
        Download BVI target tables, generate investor reporting packs, and push
        to configured output channels.
      </p>

      {error && (
        <div className="mb-6 rounded-lg border border-garbe-rot bg-white px-4 py-3 text-sm text-garbe-blau">
          {error}
        </div>
      )}

      {periods.length === 0 ? (
        <div className="bg-garbe-blau-5 rounded-lg p-8 text-center">
          <p className="text-garbe-grau">
            No reporting periods found. Create a reporting period first.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          <section className="rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-garbe-blau mb-4">
              Reporting Period
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-garbe-grau mb-1">
                  Period
                </label>
                <select
                  value={selectedPeriodId ?? ""}
                  onChange={(e) => handlePeriodChange(e.target.value)}
                  className="form-input w-full"
                >
                  {periods.map((period) => (
                    <option key={period.id} value={period.id}>
                      {formatPeriodLabel(period)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-garbe-grau mb-1">
                  Fund Filter
                </label>
                <select
                  value={selectedFund}
                  onChange={(e) => setSelectedFund(e.target.value)}
                  className="form-input w-full"
                  disabled={!selectedPeriod?.upload_id}
                >
                  <option value="">All funds</option>
                  {funds.map((fund) => (
                    <option key={fund} value={fund}>
                      {fund}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className="rounded-xl border-2 border-garbe-grun bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-garbe-blau">
                BVI Target Table
              </h2>
              <span className="rounded-full bg-garbe-grun/10 px-3 py-1 text-xs font-semibold text-garbe-grun">
                Z1 + G2
              </span>
            </div>
            <p className="text-sm text-garbe-grau mb-4">
              Download the BVI-compliant XLSX with Z1_Tenants_Leases and
              G2_Property_data sheets for the selected period.
            </p>
            <a
              href={selectedPeriodId ? periodExportUrl(selectedPeriodId) : "#"}
              download
              className={`inline-flex items-center gap-2 rounded-md px-5 py-2.5 text-sm font-semibold text-white transition-colors ${
                selectedPeriodId
                  ? "bg-garbe-grun hover:bg-garbe-grun/90"
                  : "bg-garbe-grau cursor-not-allowed pointer-events-none opacity-50"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V3" />
              </svg>
              Download BVI XLSX
            </a>
          </section>

          <section className="rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-garbe-blau mb-2">
              Investor Reporting Pack
            </h2>
            <p className="text-sm text-garbe-grau mb-4">
              ZIP bundle with BVI XLSX and PPTX slides.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handlePreview}
                disabled={!selectedPeriodId || previewLoading}
                className="rounded-md bg-garbe-blau px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-garbe-blau/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {previewLoading ? "Preparing Preview..." : "Preview Pack"}
              </button>
              <button
                onClick={openDownload}
                disabled={!selectedPeriodId}
                className="rounded-md border border-garbe-blau px-4 py-2 text-sm font-medium text-garbe-blau transition-colors hover:bg-garbe-blau-5 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Download Pack
              </button>
            </div>
          </section>

          <section className="rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold text-garbe-blau">
                  Pack Manifest
                </h2>
                <p className="text-sm text-garbe-grau">
                  Review the generated ZIP contents before downloading or
                  pushing.
                </p>
              </div>
              {preview && (
                <div className="rounded-full bg-garbe-blau-20 px-3 py-1 text-xs font-semibold text-garbe-blau">
                  {preview.file_count} files
                </div>
              )}
            </div>

            {!preview ? (
              <p className="text-sm text-garbe-grau">
                Run a preview to see the files that will be included.
              </p>
            ) : (
              <>
                <div className="mb-4 rounded-lg bg-garbe-offwhite px-4 py-3 text-sm text-garbe-blau">
                  {preview.filename}
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full border border-garbe-neutral text-sm">
                    <thead className="bg-garbe-blau-20 text-garbe-blau">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold">
                          File
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.files.map((file, index) => (
                        <tr
                          key={file}
                          className={index % 2 === 0 ? "bg-white" : "bg-garbe-offwhite"}
                        >
                          <td className="px-3 py-2">{file}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>

          <section className="rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-garbe-blau mb-4">
              Push To Channel
            </h2>
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <div>
                <label className="block text-sm font-medium text-garbe-grau mb-1">
                  Output Channel
                </label>
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value)}
                  className="form-input w-full"
                >
                  {channels.map((channel) => (
                    <option key={channel.name} value={channel.name}>
                      {channel.name} — {channel.description}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handlePush}
                disabled={!selectedPeriodId || !selectedChannel || pushLoading}
                className="rounded-md bg-garbe-turkis px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-garbe-turkis/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {pushLoading ? "Pushing..." : "Push Pack"}
              </button>
            </div>

            {pushResult && (
              <div className="mt-5 rounded-lg border border-garbe-neutral bg-garbe-offwhite px-4 py-4 text-sm text-garbe-blau">
                <p className="font-semibold mb-1">
                  {pushResult.success ? "Push succeeded" : "Push completed with errors"}
                </p>
                <p className="mb-1">Channel: {pushResult.channel}</p>
                <p className="mb-1">Files pushed: {pushResult.files_pushed}</p>
                <p>Destination: {pushResult.destination}</p>
                {pushResult.errors.length > 0 && (
                  <div className="mt-3 rounded-md border border-garbe-rot bg-white px-3 py-2">
                    <p className="font-semibold mb-2">Errors</p>
                    <ul className="space-y-1 text-xs">
                      {pushResult.errors.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
