"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface TranscriptEntry {
  role: "user" | "agent" | "system";
  text: string;
  timestamp: Date;
}

export default function VoicePage() {
  const [status, setStatus] = useState<
    "disconnected" | "connecting" | "connected" | "error"
  >("disconnected");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addEntry = useCallback((entry: TranscriptEntry) => {
    setTranscript((prev) => [...prev, entry]);
    setTimeout(() => {
      transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  function connect() {
    setStatus("connecting");
    setErrorMsg(null);

    try {
      const ws = new WebSocket("ws://localhost:7860/ws");
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        addEntry({
          role: "system",
          text: "Connected to voice agent.",
          timestamp: new Date(),
        });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript" || data.text) {
            addEntry({
              role: data.role ?? "agent",
              text: data.text ?? event.data,
              timestamp: new Date(),
            });
          }
        } catch {
          addEntry({
            role: "agent",
            text: event.data,
            timestamp: new Date(),
          });
        }
      };

      ws.onerror = () => {
        setStatus("error");
        setErrorMsg("WebSocket connection error. Is the voice server running?");
      };

      ws.onclose = () => {
        setStatus("disconnected");
        addEntry({
          role: "system",
          text: "Disconnected from voice agent.",
          timestamp: new Date(),
        });
        wsRef.current = null;
      };
    } catch (err) {
      setStatus("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to connect"
      );
    }
  }

  function disconnect() {
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }

  function sendMessage() {
    if (!inputText.trim() || !wsRef.current || status !== "connected") return;
    wsRef.current.send(JSON.stringify({ text: inputText.trim() }));
    setInputText("");
    inputRef.current?.focus();
  }

  useEffect(() => {
    if (status === "connected") {
      inputRef.current?.focus();
    }
  }, [status]);

  const statusConfig = {
    disconnected: {
      color: "bg-gray-500",
      text: "Disconnected",
      textColor: "text-gray-400",
    },
    connecting: {
      color: "bg-amber-500 animate-pulse",
      text: "Connecting...",
      textColor: "text-amber-400",
    },
    connected: {
      color: "bg-emerald-500 animate-pulse",
      text: "Connected",
      textColor: "text-emerald-400",
    },
    error: {
      color: "bg-red-500",
      text: "Error",
      textColor: "text-red-400",
    },
  };

  const currentStatus = statusConfig[status];

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-100">Voice Agent</h1>
        <p className="text-sm text-gray-400 mt-1">
          Connect to the real-time voice agent for interview practice
        </p>
      </div>

      {/* Connection Info */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${currentStatus.color}`} />
            <span className={`text-sm font-medium ${currentStatus.textColor}`}>
              {currentStatus.text}
            </span>
          </div>

          {status === "disconnected" || status === "error" ? (
            <button
              onClick={connect}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
              </svg>
              Connect
            </button>
          ) : status === "connecting" ? (
            <button
              disabled
              className="px-5 py-2.5 bg-gray-700 text-gray-400 text-sm font-medium rounded-lg flex items-center gap-2"
            >
              <div className="w-4 h-4 border-2 border-gray-500 border-t-indigo-400 rounded-full animate-spin" />
              Connecting...
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
              </svg>
              Disconnect
            </button>
          )}
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">
            Connection Details
          </h3>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-20">Endpoint</span>
              <code className="text-xs text-indigo-400 font-mono bg-gray-900 px-2 py-0.5 rounded">
                ws://localhost:7860/ws
              </code>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-20">Protocol</span>
              <span className="text-xs text-gray-400">WebSocket</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-20">Audio</span>
              <span className="text-xs text-gray-400">
                Browser microphone (permission required)
              </span>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <p className="text-sm text-red-400">{errorMsg}</p>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
          How it works
        </h2>
        <ol className="space-y-3">
          {[
            "Ensure the voice server is running on localhost:7860",
            "Click \"Connect\" to establish a WebSocket connection",
            "Grant microphone access when prompted by your browser",
            "Speak naturally - the agent will respond in real time",
            "The transcript below shows the full conversation history",
          ].map((step, idx) => (
            <li key={idx} className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-800 border border-gray-700 text-xs text-gray-400 flex items-center justify-center font-medium">
                {idx + 1}
              </span>
              <span className="text-sm text-gray-400 pt-0.5">{step}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Transcript */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-200">Transcript</h2>
          {transcript.length > 0 && (
            <button
              onClick={() => setTranscript([])}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        <div className="h-96 overflow-y-auto p-6">
          {transcript.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <svg className="w-10 h-10 mx-auto text-gray-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                </svg>
                <p className="text-sm text-gray-500">
                  No transcript yet.
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  Connect to the voice agent to start a conversation.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {transcript.map((entry, idx) => (
                <div
                  key={idx}
                  className={`flex ${
                    entry.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 ${
                      entry.role === "user"
                        ? "bg-indigo-600 text-white"
                        : entry.role === "system"
                          ? "bg-gray-800 text-gray-500 text-xs italic border border-gray-700"
                          : "bg-gray-800 text-gray-200 border border-gray-700"
                    }`}
                  >
                    {entry.role !== "system" && (
                      <p className="text-xs font-medium mb-1 opacity-60">
                        {entry.role === "user" ? "You" : "Agent"}
                      </p>
                    )}
                    <p className="text-sm leading-relaxed">{entry.text}</p>
                    <p className="text-[10px] opacity-40 mt-1.5 text-right">
                      {entry.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={transcriptEndRef} />
            </div>
          )}
        </div>

        {/* Text Input */}
        <div className="px-6 py-4 border-t border-gray-800">
          <form
            onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
            className="flex items-center gap-3"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={status === "connected" ? "Type a message..." : "Connect to start chatting"}
              disabled={status !== "connected"}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={status !== "connected" || !inputText.trim()}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
