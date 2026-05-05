"use client";

import { useEffect, useRef, useState } from "react";
import {
  type Period,
  type PptxRefreshJob,
  applyPptxRefresh,
  getPptxRefreshJob,
  listPeriods,
  pptxRefreshDownloadUrl,
  uploadPptxRefresh,
} from "@/lib/api";

type DeckState =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "processing"; job: PptxRefreshJob }
  | { phase: "proposed"; job: PptxRefreshJob }
  | { phase: "applying"; job: PptxRefreshJob }
  | { phase: "complete"; job: PptxRefreshJob }
  | { phase: "error"; message: string; job?: PptxRefreshJob };

function formatPeriodLabel(period: Period): string {
  return `${period.stichtag ?? "No stichtag"} - ${period.status}`;
}

function tokenLabel(token: unknown): string {
  if (typeof token === "string") return token;
  if (token && typeof token === "object" && "kpi_id" in token) {
    return String((token as { kpi_id?: string }).kpi_id ?? "");
  }
  return String(token);
}

export default function DecksPage() {
  const [state, setState] = useState<DeckState>({ phase: "idle" });
  const [periods, setPeriods] = useState<Period[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [periodError, setPeriodError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listPeriods()
      .then((items) => {
        setPeriods(items);
        if (items.length > 0) setSelectedPeriodId(items[0].id);
      })
      .catch((err: Error) => setPeriodError(err.message));
  }, []);

  const selectedPeriod =
    periods.find((period) => period.id === selectedPeriodId) ?? null;

  const pollJob = (id: number) => {
    const poll = async () => {
      try {
        const job = await getPptxRefreshJob(id);
        if (job.status === "proposed") {
          setState({ phase: "proposed", job });
          return;
        }
        if (job.status === "complete") {
          setState({ phase: "complete", job });
          return;
        }
        if (job.status === "error") {
          setState({
            phase: "error",
            message: job.error_message || "Deck refresh failed",
            job,
          });
          return;
        }
        setState({ phase: "processing", job });
        setTimeout(poll, 1000);
      } catch {
        setTimeout(poll, 2000);
      }
    };
    poll();
  };

  const handleFile = async (file: File) => {
    setState({ phase: "uploading" });
    try {
      const job = await uploadPptxRefresh(file);
      setState({ phase: "processing", job });
      pollJob(job.id);
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "Upload failed",
      });
    }
  };

  const handleRefresh = async () => {
    if (state.phase !== "proposed" || !selectedPeriodId) return;
    setState({ phase: "applying", job: state.job });
    try {
      const job = await applyPptxRefresh(state.job.id, selectedPeriodId);
      if (job.status === "complete") {
        setState({ phase: "complete", job });
      } else if (job.status === "error") {
        setState({
          phase: "error",
          message: job.error_message || "Deck refresh failed",
          job,
        });
      } else {
        setState({ phase: "processing", job });
        pollJob(job.id);
      }
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "Apply failed",
        job: state.job,
      });
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const proposalJob =
    state.phase === "proposed" || state.phase === "applying"
      ? state.job
      : null;
  const tokens = proposalJob?.proposals?.tokens ?? [];
  const unknownTokens = proposalJob?.proposals?.unknown_tokens ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Slide Deck Refresh</h1>

      {periodError && (
        <div className="mb-6 rounded-lg border border-garbe-rot bg-white px-4 py-3 text-sm text-garbe-rot">
          {periodError}
        </div>
      )}

      <section
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer bg-white ${
          dragOver
            ? "border-garbe-grun bg-garbe-grun-40/30"
            : "border-garbe-blau-60 hover:border-garbe-blau-40"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pptx"
          onChange={onFileSelect}
          className="hidden"
        />

        {state.phase === "idle" && (
          <div>
            <p className="text-garbe-blau-80 text-lg mb-2">
              Drop a PowerPoint deck here, or click to select
            </p>
            <p className="text-garbe-blau-40 text-sm">
              Token mode supports placeholders like {"{{total_rent}}"}.
            </p>
          </div>
        )}

        {(state.phase === "uploading" ||
          state.phase === "processing" ||
          state.phase === "applying") && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-garbe-blau-80">
              {state.phase === "applying"
                ? "Refreshing deck..."
                : "Inspecting deck..."}
            </p>
          </div>
        )}

        {state.phase === "error" && (
          <div>
            <p className="text-garbe-rot font-semibold mb-2">Error</p>
            <p className="text-garbe-rot/80 text-sm max-w-xl mx-auto whitespace-pre-wrap">
              {state.message}
            </p>
            <button
              className="mt-4 text-garbe-blau hover:underline text-sm font-semibold"
              onClick={(e) => {
                e.stopPropagation();
                setState({ phase: "idle" });
              }}
            >
              Try again
            </button>
          </div>
        )}

        {state.phase === "complete" && (
          <div>
            <p className="text-garbe-grun font-semibold text-lg mb-3">
              Deck refreshed
            </p>
            {state.job.period_status_at_refresh === "draft" && (
              <div className="mb-4 rounded-lg border border-garbe-ocker bg-garbe-ocker/10 px-4 py-3 text-sm text-garbe-blau">
                Period not finalized - values may change before close-out.
              </div>
            )}
            <a
              href={pptxRefreshDownloadUrl(state.job.id)}
              className="inline-flex rounded-md bg-garbe-grun px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-garbe-grun/90"
            >
              Download refreshed deck
            </a>
          </div>
        )}
      </section>

      {proposalJob && (
        <section className="mt-8 rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Detected Tokens</h2>

          {tokens.length === 0 ? (
            <p className="text-sm text-garbe-blau-60">
              No supported KPI tokens were found in this deck.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {tokens.map((token, index) => (
                <span
                  key={`${tokenLabel(token)}-${index}`}
                  className="rounded-full bg-garbe-blau-20 px-3 py-1 text-xs font-semibold text-garbe-blau"
                >
                  {tokenLabel(token)}
                </span>
              ))}
            </div>
          )}

          {unknownTokens.length > 0 && (
            <div className="mt-5 rounded-lg border border-garbe-ocker bg-garbe-ocker/10 px-4 py-3 text-sm text-garbe-blau">
              <p className="font-semibold mb-2">Unknown tokens</p>
              <div className="flex flex-wrap gap-2">
                {unknownTokens.map((token) => (
                  <span key={token} className="font-mono text-xs">
                    {`{{${token}}}`}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <div>
              <label className="block text-sm font-medium text-garbe-blau-80 mb-1">
                Reporting period
              </label>
              <select
                value={selectedPeriodId ?? ""}
                onChange={(e) => setSelectedPeriodId(Number(e.target.value))}
                className="form-input w-full"
              >
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {formatPeriodLabel(period)}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleRefresh}
              disabled={
                state.phase === "applying" ||
                !selectedPeriodId ||
                tokens.length === 0
              }
              className="rounded-md bg-garbe-grun px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-garbe-grun/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Refresh deck
            </button>
          </div>

          {selectedPeriod?.status === "draft" && (
            <div className="mt-5 rounded-lg border border-garbe-ocker bg-garbe-ocker/10 px-4 py-3 text-sm font-semibold text-garbe-blau">
              ⚠️ Period not finalized — values may change before close-out. Do
              not distribute this deck to investors.
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-garbe-grun"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
