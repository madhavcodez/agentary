"use client";

import { useEffect, useState, useCallback, useRef, useMemo, memo, lazy, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchMissionStatus,
  fetchMissionFindings,
} from "@/lib/api";
import { useMissionActions } from "@/lib/hooks/useMissionActions";
import { useWS } from "@/components/WebSocketProvider";
import { EventTypes } from "@/lib/types/events";
import type { WSEvent } from "@/lib/types/events";
import type {
  MissionLiveStatus,
  MissionFinding,
  MissionActivity,
} from "@/lib/types";
import FindingModal from "@/components/ui/FindingModal";
import MissionHeader from "@/components/mission/MissionHeader";
import ActivityFeed from "@/components/mission/ActivityFeed";
import SynthesizeSection from "@/components/mission/SynthesizeSection";
import { MissionSkeleton, SkeletonCard } from "@/components/ui/Skeleton";
import SectionErrorBoundary from "@/components/ui/SectionErrorBoundary";

const StructuredDataTable = lazy(() => import("@/components/mission/StructuredDataTable"));
const RunTrace = lazy(() => import("@/components/mission/RunTrace"));

import ConfidenceBadge from "@/components/ConfidenceBadge";

// ── Finding card (memoized for list performance) ────────────────────

interface FindingCardProps {
  finding: MissionFinding;
  index: number;
  onSelect: (finding: MissionFinding) => void;
}

const FindingCard = memo(function FindingCard({ finding, index, onSelect }: FindingCardProps) {
  return (
    <button
      onClick={() => onSelect(finding)}
      className="finding-reveal text-left glass-card rounded-2xl p-5 hover:shadow-[0_0_20px_4px_rgba(16,185,129,0.12)] transition-all duration-[180ms] group"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-100 line-clamp-2 group-hover:text-emerald-400 transition-colors">
          {finding.title}
        </h3>
        <ConfidenceBadge confidence={finding.confidence} />
      </div>
      <p className="text-sm text-gray-400 line-clamp-3 mb-4 leading-relaxed">
        {finding.content}
      </p>
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="bg-white/[0.06] text-gray-300 px-2.5 py-1 rounded-md border border-white/[0.06]">
            {finding.category}
          </span>
          {finding.source_type && (
            <span className="bg-white/[0.04] text-gray-400 px-2.5 py-1 rounded-md border border-white/[0.04]">
              {finding.source_type}
            </span>
          )}
        </div>
        <span className="text-gray-600 group-hover:text-gray-400 transition-colors text-xs">
          Click to expand
        </span>
      </div>
      {finding.tags && finding.tags.length > 0 && (
        <div className="flex gap-1.5 mt-3 flex-wrap">
          {finding.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="bg-emerald-500/10 text-emerald-300 px-2 py-0.5 rounded-md text-xs border border-emerald-500/15"
            >
              {tag}
            </span>
          ))}
          {finding.tags.length > 4 && (
            <span className="text-xs text-gray-500">+{finding.tags.length - 4}</span>
          )}
        </div>
      )}
    </button>
  );
});

// ── Suggested missions helper ───────────────────────────────────────

function deriveSuggestions(findings: readonly MissionFinding[]): string[] {
  const categorySet = new Set<string>();
  const tagSet = new Set<string>();

  for (const f of findings) {
    if (f.category) categorySet.add(f.category);
    for (const t of f.tags) tagSet.add(t);
  }

  const suggestions: string[] = [];
  const categories = [...categorySet];
  const tags = [...tagSet];

  if (categories.length >= 2) {
    suggestions.push(`Deep dive: Compare ${categories[0]} vs ${categories[1]} trends`);
  }
  if (tags.length > 0) {
    suggestions.push(`Explore related research on "${tags[0]}"`);
  }
  if (categories.length > 0) {
    suggestions.push(`Expand ${categories[0]} findings with additional sources`);
  }
  if (tags.length >= 2) {
    suggestions.push(`Investigate the connection between "${tags[0]}" and "${tags[1]}"`);
  }

  // Ensure we always return at most 4
  return suggestions.slice(0, 4);
}

// ── Main Page ───────────────────────────────────────────────────────

// Prefix patterns that match mission-related events
const MISSION_EVENT_PREFIXES = ["agent.", "mission.", "finding.", "run."];

function isMissionEvent(eventType: string): boolean {
  return MISSION_EVENT_PREFIXES.some((p) => eventType.startsWith(p));
}

export default function MissionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const missionId = params.missionId as string;
  const { connectionState, subscribe } = useWS();

  const [status, setStatus] = useState<MissionLiveStatus | null>(null);
  const [findings, setFindings] = useState<MissionFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"activity" | "findings" | "structured">("activity");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [selectedFinding, setSelectedFinding] = useState<MissionFinding | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const disconnectedSinceRef = useRef<number | null>(null);

  // Load mission status and findings via REST
  const loadData = useCallback(async () => {
    try {
      const [statusData, findingsData] = await Promise.all([
        fetchMissionStatus(missionId),
        fetchMissionFindings(missionId),
      ]);
      setStatus(statusData);
      setFindings(findingsData.items);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load mission");
    } finally {
      setLoading(false);
    }
  }, [missionId]);

  // Mission actions (start, stop, rerun, synthesize)
  const {
    actionLoading,
    synthesizing,
    synthesizeSuccess,
    handleStart,
    handleStop,
    handleRerun,
    handleSynthesize: handleSynthesizeReport,
  } = useMissionActions({
    missionId,
    onRefresh: loadData,
    onError: (msg) => setError(msg),
  });

  // Initial REST fetch
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Re-fetch full state on WS reconnect
  useEffect(() => {
    if (connectionState === "connected") {
      disconnectedSinceRef.current = null;
      loadData();
    } else if (connectionState === "disconnected") {
      if (disconnectedSinceRef.current === null) {
        disconnectedSinceRef.current = Date.now();
      }
    }
  }, [connectionState, loadData]);

  // Subscribe to real-time events via WebSocket
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      // Filter: only process events for this mission
      if (event.mission_id && event.mission_id !== missionId) return;

      if (!isMissionEvent(event.event_type)) return;

      // Mission state changes: update status from event data
      if (
        event.event_type === EventTypes.MISSION_COMPLETED ||
        event.event_type === EventTypes.MISSION_FAILED ||
        event.event_type === EventTypes.MISSION_STARTED ||
        event.event_type === EventTypes.RUN_STATE_CHANGED
      ) {
        loadData();
        return;
      }

      // Agent activity events: append to activities feed
      if (event.event_type.startsWith("agent.")) {
        const activityType = event.event_type.replace("agent.", "");
        const newActivity: MissionActivity = {
          id: event.correlation_id ?? `ws-${Date.now()}`,
          activity_type: activityType,
          content: typeof event.data.message === "string" ? event.data.message : typeof event.data.content === "string" ? event.data.content : activityType,
          metadata: event.data,
          confidence: typeof event.data.confidence === "number" ? event.data.confidence : null,
          created_at: event.timestamp,
        };
        setStatus((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            activities: [...prev.activities, newActivity],
          };
        });
      }

      // Finding events: refresh findings list
      if (event.event_type === EventTypes.FINDING_CREATED) {
        fetchMissionFindings(missionId)
          .then((data) => setFindings(data.items))
          .catch((err) => {
            console.error("Failed to refresh findings:", err);
          });
      }
    };

    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [missionId, subscribe, loadData]);

  // Fallback: poll if WS disconnected for >5s and mission is active
  useEffect(() => {
    if (connectionState !== "disconnected") return;
    if (!status || !["running", "queued"].includes(status.status)) return;

    const interval = setInterval(() => {
      if (
        disconnectedSinceRef.current !== null &&
        Date.now() - disconnectedSinceRef.current > 5000 &&
        !document.hidden
      ) {
        loadData();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [connectionState, status?.status, loadData]);

  // Auto-scroll activity feed (smooth)
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [status?.activities]);

  // Derive suggested missions from findings
  const suggestedMissions = useMemo(() => deriveSuggestions(findings), [findings]);


  const handleSuggestionClick = useCallback((suggestion: string) => {
    router.push(`/missions?new=1&name=${encodeURIComponent(suggestion)}`);
  }, [router]);

  if (loading) {
    return <MissionSkeleton />;
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="glass-card rounded-2xl p-8 text-center">
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => { setError(null); setLoading(true); loadData(); }}
            className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!status) return null;

  const isRunning = ["running", "queued"].includes(status.status);
  const isDone = ["completed", "failed"].includes(status.status);
  const isDraft = status.status === "draft";
  const filteredFindings = categoryFilter
    ? findings.filter((f) => f.category === categoryFilter)
    : findings;
  const categories = [...new Set(findings.map((f) => f.category))];

  // Determine current agent name for thinking indicator
  const latestActivity = status.activities.length > 0
    ? status.activities[status.activities.length - 1]
    : null;
  const rawAgentName = latestActivity?.metadata?.agent_name;
  const currentAgentName =
    (typeof rawAgentName === "string" ? rawAgentName : null) ??
    status.crew?.agents?.[0]?.name ?? "Agent";
  const currentAction = latestActivity?.activity_type ?? "researching";

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-6 text-gray-100">
      {/* ── Mission Header + Crew ──────────────────────────────────── */}
      <MissionHeader
        status={status}
        actionLoading={actionLoading}
        onStart={handleStart}
        onStop={handleStop}
        onRerun={handleRerun}
      />

      {/* ── Tabs ────────────────────────────────────────────────────── */}
      <div className="border-b border-white/[0.06]">
        <nav className="flex gap-8" role="tablist">
          {(["activity", "findings", "structured"] as const).map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-1 text-sm font-medium rounded-t-lg transition-all duration-[180ms] ${
                activeTab === tab
                  ? "glass-card border-b-2 border-emerald-400 text-emerald-400"
                  : "border-b-2 border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab === "activity" && "Live Activity"}
              {tab === "findings" && `Findings (${findings.length})`}
              {tab === "structured" && "Structured Data"}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Live Activity Feed ──────────────────────────────────────── */}
      {activeTab === "activity" && (
        <ActivityFeed
          activities={status.activities}
          isRunning={isRunning}
          isDraft={isDraft}
          currentAgentName={currentAgentName}
          currentAction={currentAction}
          feedRef={feedRef}
        />
      )}

      {/* ── Findings Panel ──────────────────────────────────────────── */}
      {activeTab === "findings" && (
        <div className="space-y-4" role="tabpanel" aria-label="Findings">
          {/* Filters */}
          {categories.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setCategoryFilter("")}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-[180ms] ${
                  !categoryFilter
                    ? "bg-white text-gray-900"
                    : "bg-white/5 text-gray-300 hover:bg-white/10"
                }`}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-[180ms] ${
                    categoryFilter === cat
                      ? "bg-white text-gray-900"
                      : "bg-white/5 text-gray-300 hover:bg-white/10"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}

          {/* Finding cards */}
          {filteredFindings.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No findings yet</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredFindings.map((finding, idx) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  index={idx}
                  onSelect={setSelectedFinding}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Structured Data Tab (lazy loaded) ─────────────────────── */}
      {activeTab === "structured" && (
        <div className="glass-card rounded-2xl overflow-hidden" role="tabpanel" aria-label="Structured Data">
          <SectionErrorBoundary section="Structured Data">
            <Suspense fallback={<SkeletonCard className="h-64" />}>
              <StructuredDataTable findings={findings} onSelectFinding={setSelectedFinding} />
            </Suspense>
          </SectionErrorBoundary>
        </div>
      )}

      {/* ── Synthesize Report CTA + Continue Research ──────────────── */}
      {status.status === "completed" && findings.length > 0 && (
        <SynthesizeSection
          findingsCount={findings.length}
          synthesizing={synthesizing}
          synthesizeSuccess={synthesizeSuccess}
          onSynthesize={handleSynthesizeReport}
          suggestedMissions={suggestedMissions}
          isDone={isDone}
          onSuggestionClick={handleSuggestionClick}
        />
      )}

      {/* ── Continue Research (when failed, outside synthesize section) */}
      {status.status === "failed" && isDone && suggestedMissions.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xs font-semibold text-gray-500 tracking-widest uppercase">
            Continue Research
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestedMissions.map((suggestion, idx) => (
              <button
                key={suggestion}
                onClick={() => handleSuggestionClick(suggestion)}
                className="stream-in glass-card rounded-xl p-4 text-left hover:shadow-[0_0_20px_4px_rgba(16,185,129,0.12)] transition-all duration-[180ms] group"
                style={{ animationDelay: `${idx * 0.08}s` }}
              >
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400/60 text-lg flex-shrink-0">+</span>
                  <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                    {suggestion}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Run Trace (lazy loaded) ─────────────────────────────────── */}
      {status.latest_run_id && (
        <SectionErrorBoundary section="Run Trace">
        <Suspense fallback={<SkeletonCard />}>
          <RunTrace runId={status.latest_run_id} />
        </Suspense>
        </SectionErrorBoundary>
      )}

      {/* ── Finding Detail Modal ─────────────────────────────────────── */}
      {selectedFinding && (
        <FindingModal
          finding={selectedFinding}
          onClose={() => setSelectedFinding(null)}
          relatedFindings={findings.filter(
            (f) => f.category === selectedFinding.category && f.id !== selectedFinding.id,
          )}
          onSelectRelated={(f) => setSelectedFinding(f)}
        />
      )}
    </div>
  );
}
