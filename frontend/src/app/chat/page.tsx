"use client";

import { useEffect, useRef, useState } from "react";
import {
  type ChatMessageItem,
  type ChatResponse,
  type ChatSession,
  type PendingConfirmation,
  deleteChatSession,
  getChatMessages,
  listChatSessions,
  sendChatMessage,
} from "@/lib/api";

interface DisplayMessage {
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls?: { tool: string; description: string }[];
  pending?: PendingConfirmation[];
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [pendingConfirms, setPendingConfirms] = useState<PendingConfirmation[]>(
    []
  );
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listChatSessions().then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const loadSession = async (id: number) => {
    setActiveSessionId(id);
    setPendingConfirms([]);
    setError("");
    try {
      const msgs = await getChatMessages(id);
      const display: DisplayMessage[] = [];
      for (const m of msgs) {
        if (m.role === "user") {
          display.push({ role: "user", content: m.content });
        } else if (m.role === "assistant" && m.content) {
          display.push({ role: "assistant", content: m.content });
        }
      }
      setMessages(display);
    } catch {
      setError("Failed to load session");
    }
  };

  const startNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setPendingConfirms([]);
    setError("");
  };

  const handleDeleteSession = async (id: number) => {
    try {
      await deleteChatSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) startNewSession();
    } catch {
      setError("Failed to delete session");
    }
  };

  const handleSend = async (
    overrideMessage?: string,
    confirmedIds?: string[]
  ) => {
    const text = overrideMessage ?? input.trim();
    if (!text && !confirmedIds?.length) return;

    setSending(true);
    setError("");

    if (text) {
      setMessages((prev) => [...prev, { role: "user", content: text }]);
    }
    if (!overrideMessage) setInput("");

    try {
      const resp: ChatResponse = await sendChatMessage({
        session_id: activeSessionId ?? undefined,
        message: text || "Confirmed.",
        confirmed_tool_calls: confirmedIds,
      });

      if (!activeSessionId) {
        setActiveSessionId(resp.session_id);
        const updated = await listChatSessions();
        setSessions(updated);
      }

      const toolCalls = resp.tool_results.map((tr) => ({
        tool: String((tr as Record<string, unknown>).tool || ""),
        description: JSON.stringify(
          (tr as Record<string, unknown>).result,
          null,
          2
        ).slice(0, 200),
      }));

      if (resp.message) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: resp.message,
            toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
            pending:
              resp.pending_confirmations.length > 0
                ? resp.pending_confirmations
                : undefined,
          },
        ]);
      }

      setPendingConfirms(resp.pending_confirmations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setSending(false);
    }
  };

  const handleConfirm = (ids: string[]) => {
    setPendingConfirms([]);
    handleSend("Confirmed — please proceed.", ids);
  };

  const handleReject = () => {
    setPendingConfirms([]);
    setMessages((prev) => [
      ...prev,
      { role: "system", content: "Edit cancelled by user." },
    ]);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <div className="w-64 border-r border-garbe-neutral bg-white flex flex-col">
        <div className="p-3 border-b border-garbe-neutral">
          <button
            onClick={startNewSession}
            className="w-full px-3 py-2 bg-garbe-blau text-white rounded text-sm hover:bg-garbe-blau-80"
          >
            + New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`flex items-center gap-1 px-3 py-2 text-sm cursor-pointer border-b border-garbe-neutral/30 ${
                s.id === activeSessionId
                  ? "bg-garbe-blau/5 text-garbe-blau"
                  : "text-garbe-blau-60 hover:bg-garbe-offwhite"
              }`}
            >
              <div
                className="flex-1 truncate"
                onClick={() => loadSession(s.id)}
              >
                {s.title || "Untitled"}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(s.id);
                }}
                className="text-garbe-blau-40 hover:text-garbe-rot text-xs px-1"
                title="Delete"
              >
                ×
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="p-3 text-xs text-garbe-blau-40">
              No conversations yet.
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-garbe-neutral bg-white">
          <h1 className="text-lg">Data Assistant</h1>
          <p className="text-xs text-garbe-blau-60">
            Ask questions about your rent roll data, investigate issues, or
            update master records.
          </p>
        </div>

        {error && (
          <div className="mx-4 mt-2 p-2 bg-garbe-rot/10 text-garbe-rot rounded text-sm">
            {error}
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-garbe-blau-40">
                <div className="text-4xl mb-3">💬</div>
                <div className="text-sm font-medium mb-1">
                  Start a conversation
                </div>
                <div className="text-xs max-w-sm">
                  Ask about tenants, properties, rents, data quality issues, or
                  request edits to master data.
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-garbe-blau text-white"
                    : msg.role === "system"
                      ? "bg-garbe-ocker/10 text-garbe-ocker border border-garbe-ocker/30"
                      : "bg-white border border-garbe-neutral text-garbe-blau"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-garbe-neutral/50">
                    <div className="text-xs text-garbe-blau-60 mb-1">
                      Tools used:
                    </div>
                    {msg.toolCalls.map((tc, j) => (
                      <div
                        key={j}
                        className="text-xs bg-garbe-offwhite rounded px-2 py-1 mb-1 font-mono"
                      >
                        {tc.tool}
                      </div>
                    ))}
                  </div>
                )}

                {msg.pending && msg.pending.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-garbe-ocker/30">
                    <div className="text-xs text-garbe-ocker font-medium mb-1">
                      Pending confirmation:
                    </div>
                    {msg.pending.map((p, j) => (
                      <div
                        key={j}
                        className="text-xs bg-garbe-ocker/10 rounded px-2 py-1 mb-1"
                      >
                        {p.description}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-garbe-neutral rounded-lg px-4 py-2 text-sm text-garbe-blau-60">
                Thinking...
              </div>
            </div>
          )}
        </div>

        {/* Confirmation bar */}
        {pendingConfirms.length > 0 && (
          <div className="mx-4 mb-2 p-3 bg-garbe-ocker/10 border border-garbe-ocker/30 rounded-lg">
            <div className="text-sm font-medium text-garbe-ocker mb-2">
              The assistant wants to make changes:
            </div>
            {pendingConfirms.map((pc) => (
              <div key={pc.tool_use_id} className="text-sm mb-1">
                {pc.description}
              </div>
            ))}
            <div className="flex gap-2 mt-3">
              <button
                onClick={() =>
                  handleConfirm(pendingConfirms.map((p) => p.tool_use_id))
                }
                className="px-4 py-1.5 bg-garbe-grun text-white rounded text-sm hover:bg-garbe-grun-80"
              >
                Approve
              </button>
              <button
                onClick={handleReject}
                className="px-4 py-1.5 bg-white border border-garbe-neutral text-garbe-blau rounded text-sm hover:bg-garbe-offwhite"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t border-garbe-neutral bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your data..."
              className="form-input flex-1"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="px-4 py-2 bg-garbe-blau text-white rounded text-sm hover:bg-garbe-blau-80 disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
