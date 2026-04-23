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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Upload CSV</h1>

      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
          dragOver
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
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
            <p className="text-gray-600 text-lg mb-2">
              Drop a Mieterliste CSV file here, or click to select
            </p>
            <p className="text-gray-400 text-sm">
              GARBE format, semicolon-delimited, latin-1 encoded
            </p>
          </div>
        )}

        {state.phase === "uploading" && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-gray-600">Uploading...</p>
          </div>
        )}

        {state.phase === "processing" && (
          <div className="flex items-center justify-center gap-3">
            <Spinner />
            <p className="text-gray-600">
              Parsing CSV (upload #{state.uploadId})...
            </p>
          </div>
        )}

        {state.phase === "error" && (
          <div>
            <p className="text-red-600 font-medium mb-2">Error</p>
            <p className="text-red-500 text-sm max-w-lg mx-auto whitespace-pre-wrap">
              {state.message}
            </p>
            <button
              className="mt-4 text-blue-600 hover:underline text-sm"
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
            <p className="text-green-600 font-medium text-lg mb-3">
              Upload complete
            </p>
            <UploadSummary detail={state.detail} />
            <button
              className="mt-4 text-blue-600 hover:underline text-sm"
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
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Previous Uploads
          </h2>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Filename
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Stichtag
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Rows
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {uploads.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-700">{u.id}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                      {u.filename}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {u.stichtag || "—"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <StatusBadge status={u.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 text-right">
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
      <div className="text-gray-500">Stichtag</div>
      <div className="text-gray-900 font-medium">{detail.stichtag}</div>
      <div className="text-gray-500">Fund</div>
      <div className="text-gray-900 font-medium">{detail.fund_label}</div>
      <div className="text-gray-500">Total rows</div>
      <div className="text-gray-900 font-medium">
        {detail.row_count?.toLocaleString()}
      </div>
      <div className="text-gray-500">Data rows</div>
      <div className="text-gray-900 font-medium">
        {detail.data_row_count?.toLocaleString()}
      </div>
      <div className="text-gray-500">Properties</div>
      <div className="text-gray-900 font-medium">
        {detail.summary_row_count}
      </div>
      <div className="text-gray-500">Orphan rows</div>
      <div className="text-gray-900 font-medium">{detail.orphan_row_count}</div>
      {detail.parser_warnings_json && detail.parser_warnings_json.length > 0 && (
        <>
          <div className="text-gray-500">Warnings</div>
          <div className="text-amber-600 font-medium">
            {detail.parser_warnings_json.length}
          </div>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    complete: "bg-green-100 text-green-700",
    processing: "bg-blue-100 text-blue-700",
    error: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
        colors[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {status}
    </span>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-blue-600"
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
