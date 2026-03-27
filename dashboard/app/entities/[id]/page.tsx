"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchEntityDetail,
  fetchEntityAliases,
  fetchEntityRelationships,
  fetchInsights,
  fetchRecommendations,
  fetchInsightEvidence,
  triggerInsightGeneration,
  fetchSignals,
  fetchProjects,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type {
  Entity,
  EntityAlias,
  EntityRelationship,
  Insight,
  IntelRecommendation,
  EvidenceItem,
  Signal,
} from "@/lib/types";
import Badge from "@/components/ui/Badge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import FreshnessIndicator from "@/components/FreshnessIndicator";
import Spinner from "@/components/ui/Spinner";
import Card from "@/components/ui/Card";

// ── Helpers ──────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const ENTITY_TYPE_VARIANT: Record<string, "success" | "info" | "warning" | "danger" | "neutral"> = {
  person: "info",
  company: "success",
  organization: "success",
  product: "warning",
  location: "neutral",
  technology: "info",
};

const PRIORITY_VARIANT: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

// ── Observation age → freshness color ────────────────────────────────

function getObservationFreshness(createdAt: string): "fresh" | "aging" | "stale" {
  const ageHours = (Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60);
  if (ageHours < 24) return "fresh";
  if (ageHours < 168) return "aging";
  return "stale";
}

const FRESHNESS_DOT: Record<string, string> = {
  fresh: "bg-emerald-400",
  aging: "bg-amber-400",
  stale: "bg-red-400",
};

// ── Source type icon ─────────────────────────────────────────────────

const SOURCE_TYPE_ICON: Record<string, string> = {
  mission: "M",
  monitor: "W",
  workflow: "F",
  voice: "V",
  user_flagged: "U",
};

export default function EntityDetailPage() {
  const params = useParams();
  const entityId = params.id as string;
  const router = useRouter();
  const { toast } = useToast();

  const [entity, setEntity] = useState<Entity | null>(null);
  const [aliases, setAliases] = useState<EntityAlias[]>([]);
  const [relationships, setRelationships] = useState<EntityRelationship[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [recommendations, setRecommendations] = useState<IntelRecommendation[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  // Insight evidence expansion
  const [expandedInsightId, setExpandedInsightId] = useState<string | null>(null);
  const [insightEvidence, setInsightEvidence] = useState<Record<string, EvidenceItem[]>>({});
  const [evidenceLoading, setEvidenceLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const entityData = await fetchEntityDetail(entityId);
      setEntity(entityData);

      let projectId = entityData.project_id;
      if (!projectId) {
        const projects = await fetchProjects();
        projectId = projects[0]?.id ?? "";
      }
      if (!projectId) {
        throw new Error("No project found for this entity");
      }

      // Load related data in parallel
      const [aliasData, relData, insightData, recData, signalData] =
        await Promise.all([
          fetchEntityAliases(entityId).catch(() => [] as EntityAlias[]),
          fetchEntityRelationships(entityId).catch(() => [] as EntityRelationship[]),
          fetchInsights({ project_id: projectId, entity_id: entityId }).catch(() => [] as Insight[]),
          fetchRecommendations({ project_id: projectId, entity_id: entityId }).catch(
            () => [] as IntelRecommendation[],
          ),
          fetchSignals({ project_id: projectId, entity_id: entityId, limit: 50 }).catch(
            () => [] as Signal[],
          ),
        ]);

      setAliases(aliasData);
      setRelationships(relData);
      setInsights(insightData);
      setRecommendations(recData);
      setSignals(signalData);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load entity");
    } finally {
      setLoading(false);
    }
  }, [entityId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExpandInsight = async (insightId: string) => {
    if (expandedInsightId === insightId) {
      setExpandedInsightId(null);
      return;
    }
    setExpandedInsightId(insightId);
    if (!insightEvidence[insightId]) {
      setEvidenceLoading(insightId);
      try {
        const ev = await fetchInsightEvidence(insightId);
        setInsightEvidence((prev) => ({ ...prev, [insightId]: ev }));
      } catch {
        setInsightEvidence((prev) => ({ ...prev, [insightId]: [] }));
      } finally {
        setEvidenceLoading(null);
      }
    }
  };

  const handleGenerateInsights = async () => {
    if (!entity) return;
    setGenerating(true);
    try {
      await triggerInsightGeneration(entity.project_id, entityId);
      toast("Insight generation triggered", "success");
      // Reload after a short delay
      setTimeout(() => load(), 2000);
    } catch {
      toast("Failed to trigger insight generation", "error");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400 text-sm">
          {error ?? "Entity not found"}
        </div>
      </div>
    );
  }

  const typeVariant = ENTITY_TYPE_VARIANT[entity.entity_type] ?? "neutral";

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-8">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-100">{entity.name}</h1>
            <Badge variant={typeVariant}>{entity.entity_type}</Badge>
            {entity.verified && (
              <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                Verified
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <ConfidenceBadge confidence={entity.confidence} />
            <span>Updated {formatDate(entity.updated_at)}</span>
          </div>
        </div>
        <button
          onClick={handleGenerateInsights}
          disabled={generating}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Insights"}
        </button>
      </div>

      {/* ── Aliases Section ────────────────────────────────────────────── */}
      {aliases.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
            Aliases
          </h2>
          <div className="flex flex-wrap gap-2">
            {aliases.map((alias) => (
              <div
                key={alias.id}
                className="flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-1.5"
              >
                <Badge variant="neutral" size="sm">
                  {alias.alias_type}
                </Badge>
                <span className="text-sm text-gray-200">{alias.alias_value}</span>
                {alias.source_name && (
                  <span className="text-xs text-gray-500">
                    via {alias.source_name}
                  </span>
                )}
                <span className="text-xs text-gray-500">
                  {Math.round(alias.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Relationships Section ──────────────────────────────────────── */}
      {relationships.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
            Relationships
          </h2>
          <div className="space-y-2">
            {relationships.map((rel) => {
              const isFrom = rel.from_entity_id === entityId;
              const relatedEntity = isFrom ? rel.to_entity : rel.from_entity;
              const relatedId = isFrom ? rel.to_entity_id : rel.from_entity_id;

              return (
                <button
                  key={rel.id}
                  onClick={() => router.push(`/entities/${relatedId}`)}
                  className="w-full text-left flex items-center gap-3 bg-gray-800/30 border border-gray-800 rounded-lg px-4 py-3 hover:border-gray-700 transition-colors"
                >
                  <Badge variant="info" size="sm">
                    {rel.relationship_type}
                  </Badge>
                  <span className="text-sm text-gray-200">
                    {relatedEntity?.name ?? relatedId}
                  </span>
                  {relatedEntity?.entity_type && (
                    <Badge variant="neutral" size="sm">
                      {relatedEntity.entity_type}
                    </Badge>
                  )}
                  <span className="text-xs text-gray-500 ml-auto">
                    {Math.round(rel.confidence * 100)}% confidence
                  </span>
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── Signals/Observations Timeline ─────────────────────────────── */}
      <Card>
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
          Signals Timeline
        </h2>
        {signals.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">
            No signals linked to this entity.
          </p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {signals.map((signal) => {
              const freshness = getObservationFreshness(signal.created_at);
              return (
                <div
                  key={signal.id}
                  className="flex items-start gap-3 bg-gray-800/30 rounded-lg px-3 py-2"
                >
                  <div className="w-7 h-7 rounded bg-gray-700/50 flex items-center justify-center text-xs font-bold text-gray-400 shrink-0 mt-0.5">
                    {SOURCE_TYPE_ICON[signal.source_type] ?? "S"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 truncate">
                      {signal.title}
                    </p>
                    {signal.content && (
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                        {signal.content}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="neutral" size="sm">
                        {signal.source_type}
                      </Badge>
                      <ConfidenceBadge confidence={signal.confidence} />
                    </div>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    <span className="text-xs text-gray-500">
                      {formatDate(signal.created_at)}
                    </span>
                    <span
                      className={`w-2 h-2 rounded-full ${FRESHNESS_DOT[freshness]}`}
                      title={freshness}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ── Insights Section ───────────────────────────────────────────── */}
      <Card>
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
          Insights
        </h2>
        {insights.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">
            No insights for this entity yet. Click &quot;Generate Insights&quot; to analyze.
          </p>
        ) : (
          <div className="space-y-3">
            {insights.map((insight) => {
              const isExpanded = expandedInsightId === insight.id;
              return (
                <div key={insight.id}>
                  <button
                    onClick={() => handleExpandInsight(insight.id)}
                    className="w-full text-left bg-gray-800/30 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge
                        variant={insight.is_active ? "success" : "neutral"}
                        size="sm"
                      >
                        {insight.insight_type}
                      </Badge>
                      {insight.is_stale && (
                        <Badge variant="danger" size="sm">stale</Badge>
                      )}
                      <ConfidenceBadge confidence={insight.confidence} />
                    </div>
                    <h3 className="text-sm font-semibold text-gray-100 mb-1">
                      {insight.title}
                    </h3>
                    {insight.content && (
                      <p className="text-xs text-gray-400 line-clamp-2">
                        {insight.content}
                      </p>
                    )}
                    <div className="mt-2">
                      <FreshnessIndicator
                        freshnessAt={insight.freshness_at}
                        thresholdHours={insight.staleness_threshold_hours}
                      />
                    </div>
                  </button>

                  {/* Evidence chain */}
                  {isExpanded && (
                    <div className="ml-4 mt-2 border-l-2 border-gray-700 pl-4 space-y-2">
                      {evidenceLoading === insight.id && (
                        <div className="flex items-center gap-2 py-2">
                          <Spinner size="sm" />
                          <span className="text-xs text-gray-500">
                            Loading evidence...
                          </span>
                        </div>
                      )}
                      {insightEvidence[insight.id]?.length === 0 && (
                        <p className="text-xs text-gray-500 py-1">
                          No evidence chain available.
                        </p>
                      )}
                      {insightEvidence[insight.id]?.map((ev) => (
                        <div
                          key={ev.id}
                          className="bg-gray-900 border border-gray-800 rounded-lg p-3"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="info" size="sm">
                              {ev.evidence_type}
                            </Badge>
                            <span className="text-xs text-gray-400">
                              Weight: {ev.weight.toFixed(2)}
                            </span>
                          </div>
                          {ev.notes && (
                            <p className="text-xs text-gray-400">{ev.notes}</p>
                          )}
                          {ev.observation && (
                            <div className="mt-2 pl-3 border-l border-gray-700">
                              <p className="text-xs font-medium text-gray-300">
                                {ev.observation.subject}
                              </p>
                              {ev.observation.content && (
                                <p className="text-xs text-gray-500 mt-0.5">
                                  {ev.observation.content}
                                </p>
                              )}
                              {ev.observation.source_url && (
                                <a
                                  href={ev.observation.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-emerald-400 hover:text-emerald-300 mt-1 inline-block"
                                >
                                  {ev.observation.source_name ?? "View source"}
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ── Recommendations Section ────────────────────────────────────── */}
      <Card>
        <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
          Recommendations
        </h2>
        {recommendations.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">
            No recommendations for this entity.
          </p>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec) => {
              const priorityVariant = PRIORITY_VARIANT[rec.priority] ?? "neutral";
              return (
                <div
                  key={rec.id}
                  className="bg-gray-800/30 border border-gray-800 rounded-lg p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={priorityVariant} size="sm">
                      {rec.priority}
                    </Badge>
                    <Badge variant="neutral" size="sm">
                      {rec.recommendation_type}
                    </Badge>
                    <Badge
                      variant={
                        rec.status === "accepted"
                          ? "success"
                          : rec.status === "rejected"
                            ? "danger"
                            : "neutral"
                      }
                      size="sm"
                    >
                      {rec.status}
                    </Badge>
                  </div>
                  <h3 className="text-sm font-semibold text-gray-100 mb-1">
                    {rec.title}
                  </h3>
                  {rec.rationale && (
                    <p className="text-xs text-gray-400 line-clamp-2">
                      {rec.rationale}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <ConfidenceBadge confidence={rec.confidence} />
                    <span>{formatDate(rec.created_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
