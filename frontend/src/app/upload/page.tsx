"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type UploadDetail,
  type UploadListItem,
  getUpload,
  listUploads,
  uploadCsv,
} from "@/lib/api";

type UploadState =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "processing"; uploadId: number }
  | { phase: "complete"; detail: UploadDetail }
  | { phase: "error"; message: string };

export default function UploadPage() {
  const [state, setState] = useState<UploadState>({ phase: "idle" });
  const [uploads, setUploads] = useState<UploadListItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshUploads = useCallback(async () => {
    try {
      const list = await listUploads();
      setUploads(list);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    refreshUploads();
  }, [refreshUploads]);

  const handleFile = async (file: File) => {
    setState({ phase: "uploading" });
    try {
      const resp = await uploadCsv(file);
      setState({ phase: "processing", uploadId: resp.id });
      pollUpload(resp.id);
    } catch (err) {
      setState({
        phase: "error",
        message: err instanceof Error ? err.message : "Upload failed",
      });
    }
  };

  const pollUpload = async (id: number) => {
    const poll = async () => {
      try {
        const detail = await getUpload(id);
        if (detail.status === "complete") {
          setState({ phase: "complete", detail });
          refreshUploads();
          return;
        }
        if (detail.status === "error") {
          setState({
            phase: "error",
            message: detail.error_message || "Processing failed",
          });
          refreshUploads();
          return;
        }
        setTimeout(poll, 1000);
      } catch {
        setTimeout(poll, 2000);
      }
    };
    poll();
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

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Upload CSV</h1>

      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
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
          accept=".csv"
          onChange={onFileSelect}
          className="hidden"
        />

        {state.phase === "idle" && (
          <div>
            <p className="text-garbe-blau-80 text-lg mb-2">
              Drop a Mieterliste CSV file here, or click to select
            </p>
            <p className="text-garbe-blau-40 text-sm">
              GARBE format, semicolon-delimited, latin-1 encoded
            </p>
          </div>
        )}

        {state.phase === "uploading" && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-garbe-blau-80">Uploading...</p>
          </div>
        )}

        {state.phase === "processing" && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-garbe-blau-80">
              Parsing CSV (upload #{state.uploadId})...
            </p>
          </div>
        )}

        {state.phase === "error" && (
          <div>
            <p className="text-garbe-rot font-semibold mb-2">Error</p>
            <p className="text-garbe-rot/80 text-sm max-w-lg mx-auto whitespace-pre-wrap">
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
              Upload complete
            </p>
            <UploadSummary detail={state.detail} />
            <button
              className="mt-4 text-garbe-blau hover:underline text-sm font-semibold"
              onClick={(e) => {
                e.stopPropagation();
                setState({ phase: "idle" });
              }}
            >
              Upload another
            </button>
          </div>
        )}
      </div>

      {uploads.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-4">Previous Uploads</h2>
          <div className="bg-white rounded-lg border border-garbe-neutral overflow-hidden">
            <table className="min-w-full divide-y divide-garbe-neutral">
              <thead className="bg-garbe-blau-20/40">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider">
                    Filename
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider">
                    Stichtag
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-garbe-blau uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-garbe-blau uppercase tracking-wider">
                    Rows
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-garbe-neutral">
                {uploads.map((u, i) => (
                  <tr
                    key={u.id}
                    className={`hover:bg-garbe-neutral/50 ${i % 2 === 1 ? "bg-garbe-offwhite" : "bg-white"}`}
                  >
                    <td className="px-4 py-3 text-sm text-garbe-blau-80">
                      {u.id}
                    </td>
                    <td className="px-4 py-3 text-sm text-garbe-blau font-medium">
                      {u.filename}
                    </td>
                    <td className="px-4 py-3 text-sm text-garbe-blau-60">
                      {u.stichtag || "—"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <StatusBadge status={u.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-garbe-blau-60 text-right">
                      {u.row_count?.toLocaleString() ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadSummary({ detail }: { detail: UploadDetail }) {
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm text-left max-w-md mx-auto">
      <div className="text-garbe-blau-60">Stichtag</div>
      <div className="text-garbe-blau font-medium">{detail.stichtag}</div>
      <div className="text-garbe-blau-60">Fund</div>
      <div className="text-garbe-blau font-medium">{detail.fund_label}</div>
      <div className="text-garbe-blau-60">Total rows</div>
      <div className="text-garbe-blau font-medium">
        {detail.row_count?.toLocaleString()}
      </div>
      <div className="text-garbe-blau-60">Data rows</div>
      <div className="text-garbe-blau font-medium">
        {detail.data_row_count?.toLocaleString()}
      </div>
      <div className="text-garbe-blau-60">Properties</div>
      <div className="text-garbe-blau font-medium">
        {detail.summary_row_count}
      </div>
      <div className="text-garbe-blau-60">Orphan rows</div>
      <div className="text-garbe-blau font-medium">
        {detail.orphan_row_count}
      </div>
      {detail.parser_warnings_json && detail.parser_warnings_json.length > 0 && (
        <>
          <div className="text-garbe-blau-60">Warnings</div>
          <div className="text-garbe-ocker font-medium">
            {detail.parser_warnings_json.length}
          </div>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    complete: "bg-garbe-grun-40/50 text-garbe-grun",
    processing: "bg-garbe-turkis/10 text-garbe-turkis",
    error: "bg-garbe-rot/10 text-garbe-rot",
  };
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
        styles[status] || "bg-garbe-neutral text-garbe-blau-60"
      }`}
    >
      {status}
    </span>
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
