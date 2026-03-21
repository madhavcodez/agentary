"use client";

import { useEffect, useState } from "react";
import type { Node } from "reactflow";

interface Props {
  node: Node | null;
  onUpdateConfig: (nodeId: string, config: Record<string, unknown>) => void;
  onUpdateLabel: (nodeId: string, label: string) => void;
  onDeleteNode: (nodeId: string) => void;
}

export default function PropertiesPanel({ node, onUpdateConfig, onUpdateLabel, onDeleteNode }: Props) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [label, setLabel] = useState("");

  useEffect(() => {
    if (node) {
      setConfig(node.data.config || {});
      setLabel(node.data.label || "");
    }
  }, [node]);

  if (!node) {
    return (
      <div className="w-72 bg-gray-900 border-l border-gray-800 p-4">
        <p className="text-sm text-gray-500 text-center mt-10">
          Select a node to edit its properties
        </p>
      </div>
    );
  }

  function handleConfigChange(key: string, value: unknown) {
    const updated = { ...config, [key]: value };
    setConfig(updated);
    onUpdateConfig(node!.id, updated);
  }

  function handleLabelChange(newLabel: string) {
    setLabel(newLabel);
    onUpdateLabel(node!.id, newLabel);
  }

  const configKeys = Object.keys(config);

  return (
    <div className="w-72 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-200">Properties</h3>
        <button
          onClick={() => onDeleteNode(node.id)}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors"
        >
          Delete
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Label</label>
          <input
            type="text"
            value={label}
            onChange={(e) => handleLabelChange(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Type</label>
          <div className="px-2.5 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-300">
            {node.data.nodeType}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">ID</label>
          <div className="px-2.5 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-500 font-mono">
            {node.id}
          </div>
        </div>

        <hr className="border-gray-800" />

        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Configuration
        </h4>

        {configKeys.length === 0 ? (
          <p className="text-xs text-gray-500">No configuration options</p>
        ) : (
          configKeys.map((key) => {
            const value = config[key];
            if (typeof value === "boolean") {
              return (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-xs text-gray-300">{key}</label>
                  <button
                    onClick={() => handleConfigChange(key, !value)}
                    className={`w-8 h-4 rounded-full transition-colors ${
                      value ? "bg-indigo-600" : "bg-gray-700"
                    }`}
                  >
                    <div
                      className={`w-3 h-3 rounded-full bg-white transform transition-transform ${
                        value ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              );
            }
            if (typeof value === "number") {
              return (
                <div key={key}>
                  <label className="block text-xs text-gray-300 mb-1">{key}</label>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => handleConfigChange(key, Number(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              );
            }
            if (Array.isArray(value)) {
              return (
                <div key={key}>
                  <label className="block text-xs text-gray-300 mb-1">{key}</label>
                  <textarea
                    value={JSON.stringify(value, null, 2)}
                    onChange={(e) => {
                      try {
                        handleConfigChange(key, JSON.parse(e.target.value));
                      } catch {}
                    }}
                    rows={3}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1.5 text-xs font-mono focus:border-indigo-500 focus:outline-none resize-none"
                  />
                </div>
              );
            }
            if (typeof value === "object" && value !== null) {
              return (
                <div key={key}>
                  <label className="block text-xs text-gray-300 mb-1">{key}</label>
                  <textarea
                    value={JSON.stringify(value, null, 2)}
                    onChange={(e) => {
                      try {
                        handleConfigChange(key, JSON.parse(e.target.value));
                      } catch {}
                    }}
                    rows={3}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1.5 text-xs font-mono focus:border-indigo-500 focus:outline-none resize-none"
                  />
                </div>
              );
            }
            return (
              <div key={key}>
                <label className="block text-xs text-gray-300 mb-1">{key}</label>
                <input
                  type="text"
                  value={String(value ?? "")}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
            );
          })
        )}

        <button
          onClick={() => {
            const key = prompt("Config key name:");
            if (key && !(key in config)) {
              handleConfigChange(key, "");
            }
          }}
          className="w-full text-xs text-indigo-400 hover:text-indigo-300 py-1.5 border border-dashed border-gray-700 rounded hover:border-indigo-500/50 transition-colors"
        >
          + Add Config Field
        </button>
      </div>
    </div>
  );
}
