"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactFlow, { Background, Controls, type Node, type Edge, type NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
import Nav from "@/components/Nav";
import { fetchWorkflow, fetchWorkflowRun } from "@/lib/api";
import type { WorkflowData, WorkflowRun, WorkflowNodeResult } from "@/lib/types";
import RunStatusNode from "@/components/workflow/nodes/RunStatusNode";

const STATUS_COLORS: Record<string, string> = {
  queued: "text-gray-400",
  running: "text-amber-400",
  completed: "text-emerald-400",
  failed: "text-red-400",
  cancelled: "text-gray-500",
};

export default function WorkflowRunPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;
  const runId = params.runId as string;

  const [workflow, setWorkflow] = useState<WorkflowData | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const nodeTypes: NodeTypes = useMemo(() => ({ runStatus: RunStatusNode }), []);

  useEffect(() => {
    fetchWorkflow(workflowId).then(setWorkflow).catch(console.error);
  }, [workflowId]);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const r = await fetchWorkflowRun(workflowId, runId);
        if (active) {
          setRun(r);
          if (r.status === "queued" || r.status === "running") {
            setTimeout(poll, 2000);
          }
        }
      } catch {
        if (active) router.push(`/workflows/${workflowId}`);
      }
    }
    poll();
    return () => { active = false; };
  }, [workflowId, runId, router]);

  if (!workflow || !run) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const nodes: Node[] = workflow.nodes.map((n) => {
    const result: WorkflowNodeResult | undefined = run.node_results[n.id];
    return {
      id: n.id,
      type: "runStatus",
      position: n.position,
      data: {
        label: n.label,
        nodeType: n.type,
        status: result?.status || "pending",
        duration: result?.duration,
        error: result?.error,
      },
    };
  });

  const edges: Edge[] = workflow.edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source_node_id,
    target: e.target_node_id,
    sourceHandle: e.source_port || "output",
    targetHandle: e.target_port || "input",
    animated: run.status === "running",
    style: { stroke: "#6366f1" },
  }));

  const selectedResult = selectedNodeId ? run.node_results[selectedNodeId] : null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      <Nav />
      <div className="ml-64 flex-1 flex flex-col">
        {/* Header */}
        <div className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/workflows/${workflowId}`)}
              className="text-sm text-gray-400 hover:text-gray-200"
            >
              &larr; Editor
            </button>
            <span className="text-gray-700">/</span>
            <h2 className="text-sm font-semibold text-gray-200">Run</h2>
            <span className={`text-sm font-medium ${STATUS_COLORS[run.status]}`}>
              {run.status}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            {run.duration_seconds !== null && (
              <span>{run.duration_seconds.toFixed(1)}s</span>
            )}
            <span>{run.trigger_type}</span>
            <span>{new Date(run.created_at).toLocaleString()}</span>
          </div>
        </div>

        <div className="flex-1 flex">
          {/* Node graph */}
          <div className="flex-1">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(null)}
              fitView
              nodesDraggable={false}
              nodesConnectable={false}
              className="bg-gray-950"
            >
              <Background color="#374151" gap={20} />
              <Controls className="!bg-gray-800 !border-gray-700 !text-gray-300" />
            </ReactFlow>
          </div>

          {/* Result panel */}
          <div className="w-80 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-gray-200 mb-4">
              {selectedNodeId ? "Node Output" : "Run Timeline"}
            </h3>

            {selectedNodeId && selectedResult ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    selectedResult.status === "completed" ? "bg-emerald-400" :
                    selectedResult.status === "running" ? "bg-amber-400 animate-pulse" :
                    selectedResult.status === "failed" ? "bg-red-400" : "bg-gray-600"
                  }`} />
                  <span className="text-xs text-gray-300">{selectedResult.status}</span>
                  {selectedResult.duration !== undefined && (
                    <span className="text-xs text-gray-500">{selectedResult.duration}s</span>
                  )}
                </div>
                {selectedResult.error && (
                  <div className="p-2 bg-red-900/20 border border-red-800 rounded text-xs text-red-300">
                    {selectedResult.error}
                  </div>
                )}
                {selectedResult.output !== undefined && (
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Output</label>
                    <pre className="p-2 bg-gray-800 border border-gray-700 rounded text-xs text-gray-300 overflow-auto max-h-96 whitespace-pre-wrap">
                      {typeof selectedResult.output === "string"
                        ? selectedResult.output
                        : JSON.stringify(selectedResult.output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {workflow.nodes.map((n) => {
                  const result = run.node_results[n.id];
                  return (
                    <button
                      key={n.id}
                      onClick={() => setSelectedNodeId(n.id)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-800 transition-colors text-left"
                    >
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        !result ? "bg-gray-600" :
                        result.status === "completed" ? "bg-emerald-400" :
                        result.status === "running" ? "bg-amber-400 animate-pulse" :
                        result.status === "failed" ? "bg-red-400" : "bg-gray-600"
                      }`} />
                      <span className="text-xs text-gray-300 truncate flex-1">{n.label}</span>
                      {result?.duration !== undefined && (
                        <span className="text-[10px] text-gray-500">{result.duration}s</span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {run.error && (
              <div className="mt-4 p-2 bg-red-900/20 border border-red-800 rounded">
                <h4 className="text-xs font-medium text-red-300 mb-1">Run Error</h4>
                <pre className="text-xs text-red-400 whitespace-pre-wrap">
                  {JSON.stringify(run.error, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
