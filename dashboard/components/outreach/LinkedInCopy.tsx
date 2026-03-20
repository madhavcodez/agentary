"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";

interface LinkedInCopyProps {
  message: string | null;
  onCopy: (text: string) => void;
  linkedinUrl?: string | null;
}

export default function LinkedInCopy({
  message,
  onCopy,
  linkedinUrl,
}: LinkedInCopyProps) {
  const [copied, setCopied] = useState(false);

  if (!message) {
    return (
      <p className="text-sm text-gray-600">
        No LinkedIn message yet. Click &quot;Generate All Channels&quot; to
        create one.
      </p>
    );
  }

  function handleCopy() {
    onCopy(message!);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const charCount = message.length;

  return (
    <div>
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 text-sm text-gray-300 whitespace-pre-wrap mb-2">
        {message}
      </div>
      <div className="flex items-center justify-between">
        <span
          className={cn(
            "text-xs font-mono",
            charCount > 300 ? "text-amber-400" : "text-gray-500",
          )}
        >
          {charCount}/300
        </span>
        <div className="flex items-center gap-2">
          {linkedinUrl && (
            <a
              href={linkedinUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium rounded-lg transition-colors border border-gray-700 flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              Open LinkedIn
            </a>
          )}
          <button
            onClick={handleCopy}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors border flex items-center gap-1.5",
              copied
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                : "bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border-purple-500/20",
            )}
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                </svg>
                Copy to Clipboard
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
