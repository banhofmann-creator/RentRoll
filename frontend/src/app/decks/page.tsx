"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  type Period,
  type PptxAiConfirmation,
  type PptxAiProposal,
  type PptxRefreshJob,
  applyPptxAiRefresh,
  applyPptxRefresh,
  getPptxRefreshJob,
  listPeriods,
  pptxRefreshDownloadUrl,
  scanPptxRefresh,
  uploadPptxRefresh,
} from "@/lib/api";

type DeckPhase =
  | "idle"
  | "uploading"
  | "processing"
  | "proposed"
  | "scanning"
  | "applying"
  | "complete"
  | "error";

interface DeckState {
  phase: DeckPhase;
  job?: PptxRefreshJob;
  message?: string;
}

interface RowSelection {
  accepted: boolean;
  scopeChoice: "portfolio" | "skip";
  kpiId: string;
}

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

function confidenceBadge(confidence?: number | null): string {
  if (confidence == null) return "—";
  return `${Math.round(confidence * 100)}%`;
}

export default function DecksPage() {
  const [state, setState] = useState<DeckState>({ phase: "idle" });
  const [periods, setPeriods] = useState<Period[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [periodError, setPeriodError] = useState<string | null>(null);
  const [rowSelections, setRowSelections] = useState<Record<number, RowSelection>>({});
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

  const aiProposals: PptxAiProposal[] = useMemo(() => {
    return state.job?.proposals?.ai_proposals ?? [];
  }, [state.job]);

  useEffect(() => {
    const next: Record<number, RowSelection> = {};
    for (const proposal of aiProposals) {
      if (proposal.kind === "mapping") {
        next[proposal.idx] = {
          accepted: true,
          scopeChoice: "portfolio",
          kpiId: proposal.kpi_id ?? "",
        };
      } else if (proposal.kind === "ambiguous_scope") {
        next[proposal.idx] = {
          accepted: false,
          scopeChoice: "skip",
          kpiId: proposal.candidate_kpi_id ?? "",
        };
      }
    }
    setRowSelections(next);
  }, [aiProposals]);

  const pollJob = (id: number, terminal: DeckPhase = "proposed") => {
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
        setState({ phase: terminal === "proposed" ? "processing" : "scanning", job });
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
      pollJob(job.id, "proposed");
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "Upload failed",
      });
    }
  };

  const handleAiScan = async () => {
    if (!state.job || !selectedPeriodId) return;
    setState({ phase: "scanning", job: state.job });
    try {
      await scanPptxRefresh(state.job.id, selectedPeriodId);
      pollJob(state.job.id, "scanning");
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "AI scan failed",
        job: state.job,
      });
    }
  };

  const handleTokenRefresh = async () => {
    if (!state.job || !selectedPeriodId) return;
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
        pollJob(job.id, "proposed");
      }
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "Apply failed",
        job: state.job,
      });
    }
  };

  const handleAiApply = async () => {
    if (!state.job || !selectedPeriodId) return;
    const confirmations: PptxAiConfirmation[] = [];
    for (const proposal of aiProposals) {
      const sel = rowSelections[proposal.idx];
      if (!sel || !sel.accepted) continue;
      if (proposal.kind === "mapping") {
        confirmations.push({ idx: proposal.idx });
      } else if (proposal.kind === "ambiguous_scope" && sel.scopeChoice === "portfolio") {
        if (!sel.kpiId) continue;
        confirmations.push({
          idx: proposal.idx,
          scope_choice: "portfolio",
          kpi_id: sel.kpiId,
        });
      }
    }
    if (confirmations.length === 0) {
      setState({
        phase: "error",
        message: "Select at least one proposal to apply.",
        job: state.job,
      });
      return;
    }
    setState({ phase: "applying", job: state.job });
    try {
      const job = await applyPptxAiRefresh(
        state.job.id,
        selectedPeriodId,
        confirmations
      );
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
        pollJob(job.id, "proposed");
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

  const job = state.job;
  const tokens = job?.proposals?.tokens ?? [];
  const unknownTokens = job?.proposals?.unknown_tokens ?? [];
  const summary = job?.proposals?.summary ?? {};
  const proposalsMode = job?.proposals?.mode ?? "token";
  const availableKpis = job?.proposals_json?.available_kpis ?? [];

  const acceptableCount = aiProposals.reduce((acc, p) => {
    const sel = rowSelections[p.idx];
    if (!sel) return acc;
    if (!sel.accepted) return acc;
    if (p.kind === "ambiguous_scope" && sel.scopeChoice !== "portfolio") return acc;
    return acc + 1;
  }, 0);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
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
              Token mode supports placeholders like {"{{total_rent}}"}. AI mode finds KPIs without tokens.
            </p>
          </div>
        )}

        {(state.phase === "uploading" ||
          state.phase === "processing" ||
          state.phase === "scanning" ||
          state.phase === "applying") && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-garbe-blau-80">
              {state.phase === "applying"
                ? "Refreshing deck..."
                : state.phase === "scanning"
                ? "Running AI scan..."
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

        {state.phase === "complete" && job && (
          <div>
            <p className="text-garbe-grun font-semibold text-lg mb-3">Deck refreshed</p>
            {job.period_status_at_refresh === "draft" && (
              <div className="mb-4 rounded-lg border border-garbe-ocker bg-garbe-ocker/10 px-4 py-3 text-sm text-garbe-blau">
                Period not finalized - values may change before close-out.
              </div>
            )}
            <a
              href={pptxRefreshDownloadUrl(job.id)}
              className="inline-flex rounded-md bg-garbe-grun px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-garbe-grun/90"
            >
              Download refreshed deck
            </a>
          </div>
        )}
      </section>

      {job && job.status !== "complete" && (
        <section className="mt-8 rounded-xl border border-garbe-neutral bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
            <div>
              <h2 className="text-lg font-semibold">
                {proposalsMode === "ai" ? "AI Proposals" : "Detected Tokens"}
              </h2>
              <p className="text-xs text-garbe-blau-60 mt-1">
                {proposalsMode === "ai"
                  ? `${summary.mappings ?? 0} mappings · ${summary.ambiguous ?? 0} ambiguous · ${summary.unsupported ?? 0} unsupported · ${summary.skipped ?? 0} skipped`
                  : `${tokens.length} token${tokens.length === 1 ? "" : "s"} found`}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <label className="block text-xs font-medium text-garbe-blau-80">
                Reporting period
              </label>
              <select
                value={selectedPeriodId ?? ""}
                onChange={(e) => setSelectedPeriodId(Number(e.target.value))}
                className="form-input w-72"
              >
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {formatPeriodLabel(period)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedPeriod?.status === "draft" && (
            <div className="mb-5 rounded-lg border border-garbe-ocker bg-garbe-ocker/10 px-4 py-3 text-sm font-semibold text-garbe-blau">
              ⚠️ Period not finalized — values may change before close-out. Do not distribute this deck to investors.
            </div>
          )}

          {proposalsMode !== "ai" && (
            <>
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

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleTokenRefresh}
                  disabled={
                    state.phase === "applying" ||
                    !selectedPeriodId ||
                    tokens.length === 0
                  }
                  className="rounded-md bg-garbe-grun px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-garbe-grun/90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Refresh deck (token mode)
                </button>
                <button
                  onClick={handleAiScan}
                  disabled={state.phase !== "proposed" || !selectedPeriodId}
                  className="rounded-md border border-garbe-blau bg-white px-5 py-2.5 text-sm font-semibold text-garbe-blau transition-colors hover:bg-garbe-blau/5 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Scan with AI for KPIs
                </button>
              </div>
            </>
          )}

          {proposalsMode === "ai" && (
            <AiProposalTable
              proposals={aiProposals}
              rowSelections={rowSelections}
              setRowSelections={setRowSelections}
              availableKpis={availableKpis}
              onApply={handleAiApply}
              onRescan={handleAiScan}
              applying={state.phase === "applying"}
              acceptableCount={acceptableCount}
              periodSelected={!!selectedPeriodId}
            />
          )}
        </section>
      )}
    </div>
  );
}

function AiProposalTable({
  proposals,
  rowSelections,
  setRowSelections,
  availableKpis,
  onApply,
  onRescan,
  applying,
  acceptableCount,
  periodSelected,
}: {
  proposals: PptxAiProposal[];
  rowSelections: Record<number, RowSelection>;
  setRowSelections: React.Dispatch<
    React.SetStateAction<Record<number, RowSelection>>
  >;
  availableKpis: string[];
  onApply: () => void;
  onRescan: () => void;
  applying: boolean;
  acceptableCount: number;
  periodSelected: boolean;
}) {
  const setRow = (idx: number, patch: Partial<RowSelection>) => {
    setRowSelections((prev) => ({
      ...prev,
      [idx]: {
        accepted: prev[idx]?.accepted ?? false,
        scopeChoice: prev[idx]?.scopeChoice ?? "skip",
        kpiId: prev[idx]?.kpiId ?? "",
        ...patch,
      },
    }));
  };

  const acceptAllMappings = () => {
    setRowSelections((prev) => {
      const next = { ...prev };
      for (const proposal of proposals) {
        if (proposal.kind === "mapping") {
          next[proposal.idx] = {
            accepted: true,
            scopeChoice: "portfolio",
            kpiId: proposal.kpi_id ?? "",
          };
        }
      }
      return next;
    });
  };

  const rejectAll = () => {
    setRowSelections((prev) => {
      const next = { ...prev };
      for (const proposal of proposals) {
        if (next[proposal.idx]) {
          next[proposal.idx] = { ...next[proposal.idx], accepted: false };
        }
      }
      return next;
    });
  };

  if (proposals.length === 0) {
    return (
      <p className="text-sm text-garbe-blau-60">
        The AI scan returned no candidates from this deck.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={acceptAllMappings}
          className="text-xs font-semibold text-garbe-blau hover:underline"
        >
          Accept all mappings
        </button>
        <span className="text-xs text-garbe-blau-40">·</span>
        <button
          type="button"
          onClick={rejectAll}
          className="text-xs font-semibold text-garbe-blau hover:underline"
        >
          Reject all
        </button>
        <span className="text-xs text-garbe-blau-40">·</span>
        <button
          type="button"
          onClick={onRescan}
          className="text-xs font-semibold text-garbe-blau hover:underline"
        >
          Re-run AI scan
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-garbe-neutral">
        <table className="min-w-full text-sm">
          <thead className="bg-garbe-blau-10 text-garbe-blau">
            <tr>
              <th className="px-3 py-2 text-left font-semibold">Apply</th>
              <th className="px-3 py-2 text-left font-semibold">Slide</th>
              <th className="px-3 py-2 text-left font-semibold">Original</th>
              <th className="px-3 py-2 text-left font-semibold">Label / Context</th>
              <th className="px-3 py-2 text-left font-semibold">KPI / Decision</th>
              <th className="px-3 py-2 text-left font-semibold">New value</th>
              <th className="px-3 py-2 text-left font-semibold">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {proposals.map((p) => {
              const sel = rowSelections[p.idx] ?? {
                accepted: false,
                scopeChoice: "skip" as const,
                kpiId: "",
              };
              const isApplyable =
                p.kind === "mapping" || p.kind === "ambiguous_scope";
              const rowTone =
                p.kind === "unsupported_kpi" || p.kind === "skipped"
                  ? "bg-garbe-neutral/30 text-garbe-blau-60"
                  : "bg-white";
              return (
                <tr key={p.idx} className={`${rowTone} border-t border-garbe-neutral align-top`}>
                  <td className="px-3 py-2">
                    {isApplyable ? (
                      <input
                        type="checkbox"
                        checked={sel.accepted}
                        onChange={(e) =>
                          setRow(p.idx, {
                            accepted: e.target.checked,
                            scopeChoice:
                              p.kind === "ambiguous_scope" && e.target.checked
                                ? "portfolio"
                                : sel.scopeChoice,
                          })
                        }
                      />
                    ) : (
                      <span className="text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <div className="font-semibold text-garbe-blau">
                      Slide {p.slide_idx + 1}
                    </div>
                    {p.slide_title && (
                      <div className="text-xs text-garbe-blau-60 max-w-[10rem] truncate">
                        {p.slide_title}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-pre-wrap break-words max-w-[14rem]">
                    {p.original_value}
                  </td>
                  <td className="px-3 py-2 text-xs whitespace-pre-wrap break-words max-w-[16rem]">
                    {p.label_context || p.label_observed || (
                      <span className="text-garbe-blau-40">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {p.kind === "mapping" && (
                      <div>
                        <span className="font-mono font-semibold text-garbe-blau">
                          {p.kpi_id}
                        </span>
                        <div className="text-garbe-blau-60">portfolio</div>
                      </div>
                    )}
                    {p.kind === "ambiguous_scope" && (
                      <div className="space-y-1">
                        <span className="inline-block rounded-full bg-garbe-ocker/20 px-2 py-0.5 text-[10px] font-semibold uppercase text-garbe-blau">
                          Ambiguous scope
                        </span>
                        <select
                          value={sel.scopeChoice}
                          onChange={(e) =>
                            setRow(p.idx, {
                              scopeChoice: e.target.value as "portfolio" | "skip",
                              accepted: e.target.value === "portfolio",
                            })
                          }
                          className="form-input w-full text-xs"
                        >
                          <option value="skip">Skip</option>
                          <option value="portfolio">Apply at portfolio scope</option>
                        </select>
                        {sel.scopeChoice === "portfolio" && (
                          <select
                            value={sel.kpiId}
                            onChange={(e) =>
                              setRow(p.idx, { kpiId: e.target.value })
                            }
                            className="form-input w-full text-xs"
                          >
                            <option value="">Pick a KPI…</option>
                            {availableKpis.map((kpi) => (
                              <option key={kpi} value={kpi}>
                                {kpi}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}
                    {p.kind === "unsupported_kpi" && (
                      <div>
                        <span className="inline-block rounded-full bg-garbe-rot/20 px-2 py-0.5 text-[10px] font-semibold uppercase text-garbe-rot">
                          Not in catalog
                        </span>
                        {p.label_observed && (
                          <div className="text-garbe-blau-60 mt-1">
                            {p.label_observed}
                          </div>
                        )}
                      </div>
                    )}
                    {p.kind === "skipped" && (
                      <div>
                        <span className="inline-block rounded-full bg-garbe-blau-20 px-2 py-0.5 text-[10px] font-semibold uppercase text-garbe-blau">
                          Skipped
                        </span>
                        {p.reasoning && (
                          <div className="text-garbe-blau-60 mt-1">{p.reasoning}</div>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {p.new_value ?? <span className="text-garbe-blau-40">—</span>}
                  </td>
                  <td className="px-3 py-2 text-xs">{confidenceBadge(p.confidence)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button
          onClick={onApply}
          disabled={applying || acceptableCount === 0 || !periodSelected}
          className="rounded-md bg-garbe-grun px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-garbe-grun/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {applying
            ? "Applying..."
            : `Apply ${acceptableCount} confirmed mapping${acceptableCount === 1 ? "" : "s"}`}
        </button>
      </div>
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
