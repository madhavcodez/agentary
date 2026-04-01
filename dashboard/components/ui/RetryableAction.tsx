"use client";

import { useState, useCallback } from "react";

interface RetryableActionProps {
  /** The async action to execute. */
  action: () => Promise<void>;
  /** Button label. */
  label: string;
  /** Label shown while action is in progress. */
  loadingLabel?: string;
  /** Additional button classes. */
  className?: string;
  /** Disable the button externally. */
  disabled?: boolean;
}

/**
 * A button that executes an async action with automatic error display
 * and a retry mechanism. Shows an inline error message with retry option.
 */
export default function RetryableAction({
  action,
  label,
  loadingLabel,
  className = "",
  disabled = false,
}: RetryableActionProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(false);
    }
  }, [action]);

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <button
        onClick={execute}
        disabled={disabled || loading}
        className={className}
      >
        {loading ? (loadingLabel ?? label) : label}
      </button>
      {error && (
        <button
          onClick={execute}
          className="text-[11px] text-red-400 hover:text-red-300 transition-colors"
        >
          Failed — tap to retry
        </button>
      )}
    </div>
  );
}
