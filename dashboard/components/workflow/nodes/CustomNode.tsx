import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

const CATEGORY_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  trigger: { bg: "bg-purple-900/40", border: "border-purple-600/50", icon: "&#9889;" },
  research: { bg: "bg-blue-900/40", border: "border-blue-600/50", icon: "&#128269;" },
  data: { bg: "bg-emerald-900/40", border: "border-emerald-600/50", icon: "&#128202;" },
  analysis: { bg: "bg-amber-900/40", border: "border-amber-600/50", icon: "&#129504;" },
  output: { bg: "bg-rose-900/40", border: "border-rose-600/50", icon: "&#128228;" },
  control: { bg: "bg-cyan-900/40", border: "border-cyan-600/50", icon: "&#128260;" },
};

const NODE_CATEGORIES: Record<string, string> = {
  manual_trigger: "trigger",
  schedule_trigger: "trigger",
  webhook_trigger: "trigger",
  web_search: "research",
  api_query: "research",
  web_scrape: "research",
  voice_call: "research",
  expert_research: "research",
  filter: "data",
  transform: "data",
  merge: "data",
  deduplicate: "data",
  sort: "data",
  aggregate: "data",
  ai_analyze: "analysis",
  compare: "analysis",
  trend_detect: "analysis",
  generate_report: "output",
  generate_chart: "output",
  export_data: "output",
  send_email: "output",
  send_alert: "output",
  save_findings: "output",
  condition: "control",
  loop: "control",
  delay: "control",
  human_review: "control",
};

function CustomNode({ data, selected }: NodeProps) {
  const category = NODE_CATEGORIES[data.nodeType] || "data";
  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES.data;
  const hasMultipleOutputs = data.nodeType === "condition" || data.nodeType === "human_review";
  const hasMultipleInputs = data.nodeType === "merge" || data.nodeType === "compare";
  const isTrigger = category === "trigger";

  return (
    <div
      className={`min-w-[160px] rounded-lg border ${style.border} ${style.bg} px-3 py-2 ${
        selected ? "ring-2 ring-indigo-400 ring-offset-1 ring-offset-gray-950" : ""
      }`}
    >
      {!isTrigger && (
        <>
          {hasMultipleInputs ? (
            <>
              <Handle type="target" position={Position.Top} id="input_a" style={{ left: "30%", background: "#6b7280" }} />
              <Handle type="target" position={Position.Top} id="input_b" style={{ left: "70%", background: "#6b7280" }} />
            </>
          ) : (
            <Handle type="target" position={Position.Top} id="input" style={{ background: "#6b7280" }} />
          )}
        </>
      )}
      <div className="flex items-center gap-2">
        <span className="text-sm" dangerouslySetInnerHTML={{ __html: style.icon }} />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-gray-200 truncate">{data.label}</div>
          <div className="text-[10px] text-gray-500">{data.nodeType}</div>
        </div>
      </div>
      {hasMultipleOutputs ? (
        <>
          <Handle type="source" position={Position.Bottom} id="true" style={{ left: "30%", background: "#22c55e" }} />
          <Handle type="source" position={Position.Bottom} id="false" style={{ left: "70%", background: "#ef4444" }} />
        </>
      ) : (
        <Handle type="source" position={Position.Bottom} id="output" style={{ background: "#6b7280" }} />
      )}
    </div>
  );
}

export default memo(CustomNode);
