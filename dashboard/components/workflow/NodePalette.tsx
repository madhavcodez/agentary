"use client";

import { useState } from "react";

interface Props {
  onAddNode: (nodeType: string, label: string) => void;
}

const NODE_CATEGORIES = [
  {
    name: "Triggers",
    color: "text-purple-400",
    nodes: [
      { type: "manual_trigger", label: "Manual Trigger" },
      { type: "schedule_trigger", label: "Schedule Trigger" },
      { type: "webhook_trigger", label: "Webhook Trigger" },
    ],
  },
  {
    name: "Research",
    color: "text-blue-400",
    nodes: [
      { type: "web_search", label: "Web Search" },
      { type: "api_query", label: "API Query" },
      { type: "web_scrape", label: "Web Scrape" },
      { type: "voice_call", label: "Voice Call" },
      { type: "expert_research", label: "Expert Research" },
    ],
  },
  {
    name: "Data",
    color: "text-emerald-400",
    nodes: [
      { type: "filter", label: "Filter" },
      { type: "transform", label: "Transform" },
      { type: "merge", label: "Merge" },
      { type: "deduplicate", label: "Deduplicate" },
      { type: "sort", label: "Sort" },
      { type: "aggregate", label: "Aggregate" },
    ],
  },
  {
    name: "Analysis",
    color: "text-amber-400",
    nodes: [
      { type: "ai_analyze", label: "AI Analysis" },
      { type: "compare", label: "Compare" },
      { type: "trend_detect", label: "Trend Detection" },
    ],
  },
  {
    name: "Output",
    color: "text-rose-400",
    nodes: [
      { type: "generate_report", label: "Generate Report" },
      { type: "generate_chart", label: "Generate Chart" },
      { type: "export_data", label: "Export Data" },
      { type: "send_email", label: "Send Email" },
      { type: "send_alert", label: "Send Alert" },
      { type: "save_findings", label: "Save Findings" },
    ],
  },
  {
    name: "Control Flow",
    color: "text-cyan-400",
    nodes: [
      { type: "condition", label: "Condition" },
      { type: "loop", label: "Loop" },
      { type: "delay", label: "Delay" },
      { type: "human_review", label: "Human Review" },
    ],
  },
];

export default function NodePalette({ onAddNode }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    Triggers: true,
    Research: true,
    Data: true,
    Analysis: true,
    Output: true,
    "Control Flow": true,
  });

  return (
    <div className="w-56 bg-gray-900 border-r border-gray-800 overflow-y-auto p-3 space-y-2">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 mb-2">
        Node Palette
      </h3>
      {NODE_CATEGORIES.map((cat) => (
        <div key={cat.name}>
          <button
            onClick={() =>
              setExpanded((prev) => ({ ...prev, [cat.name]: !prev[cat.name] }))
            }
            className={`w-full flex items-center justify-between px-2 py-1.5 text-xs font-medium ${cat.color} hover:bg-gray-800 rounded`}
          >
            {cat.name}
            <span className="text-gray-600">{expanded[cat.name] ? "−" : "+"}</span>
          </button>
          {expanded[cat.name] && (
            <div className="ml-1 mt-1 space-y-0.5">
              {cat.nodes.map((node) => (
                <button
                  key={node.type}
                  onClick={() => onAddNode(node.type, node.label)}
                  className="w-full text-left px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-800 hover:text-gray-100 rounded transition-colors"
                >
                  {node.label}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
