"use client";

import type { MissionFinding } from "@/lib/types";
import ConfidenceBadge from "@/components/ConfidenceBadge";

interface StructuredDataTableProps {
  findings: MissionFinding[];
  onSelectFinding: (f: MissionFinding) => void;
}

export default function StructuredDataTable({ findings, onSelectFinding }: StructuredDataTableProps) {
  if (findings.length === 0) {
    return <div className="text-center py-12 text-gray-500">No data points yet</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-white/[0.06]">
        <thead className="bg-white/[0.02]">
          <tr>
            {["Title", "Category", "Confidence", "Source", "Content"].map((h) => (
              <th key={h} className="px-5 py-3.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {findings.map((f) => (
            <tr
              key={f.id}
              onClick={() => onSelectFinding(f)}
              className="hover:bg-white/[0.03] cursor-pointer transition-colors duration-[180ms]"
            >
              <td className="px-5 py-3.5 text-sm font-medium text-gray-100 max-w-[200px] truncate">
                {f.title}
              </td>
              <td className="px-5 py-3.5">
                <span className="bg-white/[0.06] text-gray-300 px-2.5 py-1 rounded-md text-xs border border-white/[0.06]">
                  {f.category}
                </span>
              </td>
              <td className="px-5 py-3.5">
                <ConfidenceBadge confidence={f.confidence} />
              </td>
              <td className="px-5 py-3.5 text-sm text-gray-400 max-w-[150px] truncate">
                {f.source_name || f.source_url || "N/A"}
              </td>
              <td className="px-5 py-3.5 text-sm text-gray-400 max-w-[300px] truncate">
                {f.content}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
