"use client";

import Button from "@/components/ui/Button";

interface EmailEditorProps {
  subject: string | null;
  body: string;
  onBodyChange: (value: string) => void;
  onSend: () => void;
  sending: boolean;
  hasEmail: boolean;
}

export default function EmailEditor({
  subject,
  body,
  onBodyChange,
  onSend,
  sending,
  hasEmail,
}: EmailEditorProps) {
  if (!hasEmail) {
    return (
      <p className="text-sm text-gray-600">
        No email draft yet. Click &quot;Generate All Channels&quot; to create
        one.
      </p>
    );
  }

  return (
    <>
      {subject && (
        <div className="mb-2">
          <span className="text-[10px] text-gray-500 uppercase">Subject:</span>
          <p className="text-sm text-gray-300">{subject}</p>
        </div>
      )}
      <textarea
        value={body}
        onChange={(e) => onBodyChange(e.target.value)}
        placeholder="No email draft yet."
        rows={6}
        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 focus:outline-none resize-none font-mono transition-colors"
      />
      <Button
        variant="primary"
        size="sm"
        loading={sending}
        disabled={!body.trim()}
        onClick={onSend}
        className="mt-2 bg-blue-600 hover:bg-blue-500"
      >
        {sending ? "Sending..." : "Send Email"}
      </Button>
    </>
  );
}
