"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import ReactFlow, {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  Controls,
  MiniMap,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import Nav from "@/components/Nav";
import {
  fetchWorkflow,
  updateWorkflow,
  activateWorkflow,
  pauseWorkflow,
  triggerWorkflowRun,
  validateWorkflowApi,
} from "@/lib/api";
import type { WorkflowData, WorkflowNode, WorkflowEdge } from "@/lib/types";
import NodePalette from "@/components/workflow/NodePalette";
import PropertiesPanel from "@/components/workflow/PropertiesPanel";
import WorkflowToolbar from "@/components/workflow/WorkflowToolbar";
import CustomNode from "@/components/workflow/nodes/CustomNode";

function wfNodesToRF(nodes: WorkflowNode[]): Node[] {
  return nodes.map((n) => ({
    id: n.id,
    type: "custom",
    position: n.position,
    data: { label: n.label, nodeType: n.type, config: n.config },
  }));
}

function wfEdgesToRF(edges: WorkflowEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `e-${e.source_node_id}-${e.target_node_id}-${i}`,
    source: e.source_node_id,
    target: e.target_node_id,
    sourceHandle: e.source_port || "output",
    targetHandle: e.target_port || "input",
    animated: true,
    style: { stroke: "#6366f1" },
  }));
}

function rfNodesToWF(nodes: Node[]): WorkflowNode[] {
  return nodes.map((n) => ({
    id: n.id,
    type: n.data.nodeType,
    label: n.data.label,
    config: n.data.config || {},
    position: n.position,
  }));
}

function rfEdgesToWF(edges: Edge[]): WorkflowEdge[] {
  return edges.map((e) => ({
    source_node_id: e.source,
    target_node_id: e.target,
    source_port: e.sourceHandle || "output",
    target_port: e.targetHandle || "input",
  }));
}

export default function WorkflowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const workflowId = params.id as string;

  const [workflow, setWorkflow] = useState<WorkflowData | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const nodeTypes: NodeTypes = useMemo(() => ({ custom: CustomNode }), []);

  useEffect(() => {
    fetchWorkflow(workflowId)
      .then((wf) => {
        setWorkflow(wf);
        setNodes(wfNodesToRF(wf.nodes));
        setEdges(wfEdgesToRF(wf.edges));
      })
      .catch((err) => {
        toast(err instanceof Error ? err.message : "Failed to load workflow", "error");
        router.push("/workflows");
      });
  }, [workflowId, router]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
      setDirty(true);
    },
    [],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((eds) => applyEdgeChanges(changes, eds));
      setDirty(true);
    },
    [],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge({ ...connection, animated: true, style: { stroke: "#6366f1" } }, eds),
      );
      setDirty(true);
    },
    [],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  function handleAddNode(nodeType: string, label: string) {
    const id = `node_${Date.now()}`;
    const newNode: Node = {
      id,
      type: "custom",
      position: { x: 250, y: nodes.length * 120 + 50 },
      data: { label, nodeType, config: {} },
    };
    setNodes((prev) => [...prev, newNode]);
    setDirty(true);
  }

  function handleUpdateNodeConfig(nodeId: string, config: Record<string, unknown>) {
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, config } } : n,
      ),
    );
    setDirty(true);
  }

  function handleUpdateNodeLabel(nodeId: string, label: string) {
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, label } } : n,
      ),
    );
    setDirty(true);
  }

  function handleDeleteNode(nodeId: string) {
    setNodes((prev) => prev.filter((n) => n.id !== nodeId));
    setEdges((prev) => prev.filter((e) => e.source !== nodeId && e.target !== nodeId));
    if (selectedNode?.id === nodeId) setSelectedNode(null);
    setDirty(true);
  }

  async function handleSave() {
    if (!workflow) return;
    setSaving(true);
    try {
      const updated = await updateWorkflow(workflowId, {
        nodes: rfNodesToWF(nodes),
        edges: rfEdgesToWF(edges),
      });
      setWorkflow(updated);
      setDirty(false);
      toast("Workflow saved", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to save workflow", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    try {
      const result = await validateWorkflowApi(workflowId);
      setValidationErrors(result.errors);
      return result.valid;
    } catch (e) {
      toast(e instanceof Error ? e.message : "Validation failed", "error");
      return false;
    }
  }

  async function handleRun() {
    if (dirty) await handleSave();
    try {
      const run = await triggerWorkflowRun(workflowId);
      router.push(`/workflows/${workflowId}/runs/${run.id}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to run workflow", "error");
    }
  }

  async function handleActivate() {
    if (!workflow) return;
    try {
      if (workflow.status === "active") {
        const updated = await pauseWorkflow(workflowId);
        setWorkflow(updated);
        toast("Workflow paused", "success");
      } else {
        const updated = await activateWorkflow(workflowId);
        setWorkflow(updated);
        toast("Workflow activated", "success");
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to update workflow", "error");
    }
  }

  if (!workflow) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      <Nav />
      <div className="ml-64 flex-1 flex flex-col">
        <WorkflowToolbar
          workflow={workflow}
          dirty={dirty}
          saving={saving}
          validationErrors={validationErrors}
          onSave={handleSave}
          onValidate={handleValidate}
          onRun={handleRun}
          onActivate={handleActivate}
        />
        <div className="flex-1 flex">
          <NodePalette onAddNode={handleAddNode} />
          <div className="flex-1 relative">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              className="bg-gray-950"
            >
              <Background color="#374151" gap={20} />
              <Controls className="!bg-gray-800 !border-gray-700 !text-gray-300" />
              <MiniMap
                nodeColor="#6366f1"
                maskColor="rgba(0,0,0,0.7)"
                className="!bg-gray-900 !border-gray-700"
              />
            </ReactFlow>
          </div>
          <PropertiesPanel
            node={selectedNode}
            onUpdateConfig={handleUpdateNodeConfig}
            onUpdateLabel={handleUpdateNodeLabel}
            onDeleteNode={handleDeleteNode}
          />
        </div>
      </div>
    </div>
  );
}
