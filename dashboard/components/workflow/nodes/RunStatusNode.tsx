import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

const STATUS_STYLES: Record<string, { ring: string; bg: string; dot: string }> = {
  pending: { ring: "ring-gray-700", bg: "bg-gray-900/60", dot: "bg-gray-600" },
  running: { ring: "ring-amber-500", bg: "bg-amber-900/20", dot: "bg-amber-400 animate-pulse" },
  completed: { ring: "ring-emerald-500", bg: "bg-emerald-900/20", dot: "bg-emerald-400" },
  failed: { ring: "ring-red-500", bg: "bg-red-900/20", dot: "bg-red-400" },
};

function RunStatusNode({ data }: NodeProps) {
  const status = data.status || "pending";
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
  const isTrigger = data.nodeType?.endsWith("_trigger");

  return (
    <div
      className={`min-w-[160px] rounded-lg border border-gray-700 ${style.bg} ring-1 ${style.ring} px-3 py-2`}
    >
      {!isTrigger && (
        <Handle type="target" position={Position.Top} id="input" style={{ background: "#6b7280" }} />
      )}
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-gray-200 truncate">{data.label}</div>
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-gray-500">{data.nodeType}</span>
            {data.duration !== undefined && (
              <span className="text-[10px] text-gray-500">({data.duration}s)</span>
            )}
          </div>
        </div>
      </div>
      {data.error && (
        <div className="mt-1 text-[10px] text-red-400 truncate">{data.error}</div>
      )}
      <Handle type="source" position={Position.Bottom} id="output" style={{ background: "#6b7280" }} />
    </div>
  );
}

export default memo(RunStatusNode);
