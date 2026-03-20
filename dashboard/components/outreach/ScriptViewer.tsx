"use client";

interface ScriptViewerProps {
  scriptJson: Record<string, unknown> | null;
}

export default function ScriptViewer({ scriptJson }: ScriptViewerProps) {
  if (!scriptJson || Object.keys(scriptJson).length === 0) {
    return (
      <p className="text-sm text-gray-600">
        No call script yet. Click &quot;Generate All Channels&quot; to create one.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {Object.entries(scriptJson).map(([key, value]) => (
        <div key={key}>
          <h5 className="text-xs font-medium text-gray-400 capitalize mb-1">
            {key.replace(/_/g, " ")}
          </h5>
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm text-gray-300">
            {typeof value === "string"
              ? value
              : Array.isArray(value)
                ? (value as unknown[]).map((item, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 mb-1 last:mb-0"
                    >
                      <span className="text-indigo-400 mt-0.5">&#8226;</span>
                      <span>
                        {typeof item === "string"
                          ? item
                          : JSON.stringify(item)}
                      </span>
                    </div>
                  ))
                : JSON.stringify(value, null, 2)}
          </div>
        </div>
      ))}
    </div>
  );
}
