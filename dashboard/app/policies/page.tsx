"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
} from "@/lib/api";
import type { Policy } from "@/lib/types";
import PolicyEditor from "@/components/PolicyEditor";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPolicies();
      setPolicies(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch policies"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(data: {
    name: string;
    description: string;
    rules_json: Record<string, unknown> | unknown[];
    is_active: boolean;
  }) {
    setSaving(true);
    try {
      await createPolicy({
        name: data.name,
        description: data.description || null,
        rules_json: data.rules_json,
        is_active: data.is_active,
      });
      setShowEditor(false);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create policy"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(data: {
    name: string;
    description: string;
    rules_json: Record<string, unknown> | unknown[];
    is_active: boolean;
  }) {
    if (!editingPolicy) return;
    setSaving(true);
    try {
      await updatePolicy(editingPolicy.id, {
        name: data.name,
        description: data.description || null,
        rules_json: data.rules_json,
        is_active: data.is_active,
      });
      setEditingPolicy(null);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update policy"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await deletePolicy(id);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete policy"
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleToggleActive(policy: Policy) {
    try {
      await updatePolicy(policy.id, { is_active: !policy.is_active });
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to toggle policy"
      );
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Policies</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage rules that govern the voice agent and matching behavior
          </p>
        </div>
        {!showEditor && !editingPolicy && (
          <button
            onClick={() => setShowEditor(true)}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Policy
          </button>
        )}
      </div>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-xs text-red-500 hover:text-red-300 mt-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* New Policy Editor */}
      {showEditor && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-base font-semibold text-gray-200 mb-4">
            Create New Policy
          </h2>
          <PolicyEditor
            onSave={handleCreate}
            onCancel={() => setShowEditor(false)}
            saving={saving}
          />
        </div>
      )}

      {/* Edit Policy Editor */}
      {editingPolicy && (
        <div className="bg-gray-900 border border-indigo-500/20 rounded-xl p-6 mb-6">
          <h2 className="text-base font-semibold text-gray-200 mb-4">
            Edit: {editingPolicy.name}
          </h2>
          <PolicyEditor
            initialName={editingPolicy.name}
            initialDescription={editingPolicy.description ?? ""}
            initialRulesJson={JSON.stringify(editingPolicy.rules_json, null, 2)}
            initialActive={editingPolicy.is_active}
            onSave={handleUpdate}
            onCancel={() => setEditingPolicy(null)}
            saving={saving}
          />
        </div>
      )}

      {/* Policy List */}
      {loading ? (
        <div className="text-center py-16">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading policies...</p>
        </div>
      ) : policies.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-gray-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
          </svg>
          <p className="text-sm text-gray-500">No policies defined yet.</p>
          <p className="text-xs text-gray-600 mt-1">
            Create your first policy to customize agent behavior.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {policies.map((policy) => (
            <div
              key={policy.id}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-base font-semibold text-gray-200 truncate">
                      {policy.name}
                    </h3>
                    <button
                      onClick={() => handleToggleActive(policy)}
                      className={`shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        policy.is_active ? "bg-indigo-500" : "bg-gray-700"
                      }`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                          policy.is_active ? "translate-x-4.5" : "translate-x-1"
                        }`}
                        style={{
                          transform: policy.is_active
                            ? "translateX(16px)"
                            : "translateX(3px)",
                        }}
                      />
                    </button>
                    <span
                      className={`text-xs font-medium ${
                        policy.is_active ? "text-indigo-400" : "text-gray-500"
                      }`}
                    >
                      {policy.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  {policy.description && (
                    <p className="text-sm text-gray-400 mb-2">
                      {policy.description}
                    </p>
                  )}
                  <div className="mt-2">
                    <details className="group">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 transition-colors">
                        View rules JSON
                      </summary>
                      <pre className="mt-2 bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto max-h-48">
                        {JSON.stringify(policy.rules_json, null, 2)}
                      </pre>
                    </details>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => {
                      setEditingPolicy(policy);
                      setShowEditor(false);
                    }}
                    className="p-2 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(policy.id)}
                    disabled={deletingId === policy.id}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
                    title="Delete"
                  >
                    {deletingId === policy.id ? (
                      <div className="w-4 h-4 border-2 border-gray-600 border-t-red-400 rounded-full animate-spin" />
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-800 text-xs text-gray-600">
                <span>Created: {new Date(policy.created_at).toLocaleDateString()}</span>
                <span>Updated: {new Date(policy.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
