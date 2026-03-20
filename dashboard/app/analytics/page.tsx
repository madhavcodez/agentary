"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  FunnelData,
  ChannelPerformance,
  ActivityTimeline,
  ScoreDistribution,
} from "@/lib/types";
import {
  fetchFunnel,
  fetchChannelPerformance,
  fetchActivityTimeline,
  fetchScoreDistribution,
} from "@/lib/api";

// ── Stage label map ─────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
  lead: "Lead",
  contacted: "Contacted",
  aware: "Aware",
  engaged: "Engaged",
  meeting: "Meeting",
  closed_won: "Closed Won",
};

// ── Helpers ─────────────────────────────────────────────────────────

function rateColor(rate: number): string {
  if (rate >= 20) return "text-emerald-400";
  if (rate >= 10) return "text-amber-400";
  return "text-red-400";
}

function bucketColor(bucket: string): string {
  const low = parseInt(bucket.split("-")[0], 10);
  if (low >= 60) return "bg-emerald-500";
  if (low >= 30) return "bg-amber-500";
  return "bg-red-500";
}

// ── Skeleton ────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 animate-pulse">
      <div className="h-5 w-40 bg-gray-800 rounded mb-4" />
      <div className="space-y-3">
        <div className="h-4 w-full bg-gray-800 rounded" />
        <div className="h-4 w-3/4 bg-gray-800 rounded" />
        <div className="h-4 w-1/2 bg-gray-800 rounded" />
      </div>
    </div>
  );
}

// ── Error state ─────────────────────────────────────────────────────

function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="bg-gray-900 border border-red-900/50 rounded-xl p-6 text-center">
      <p className="text-sm text-red-400 mb-3">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [channel, setChannel] = useState<ChannelPerformance | null>(null);
  const [timeline, setTimeline] = useState<ActivityTimeline | null>(null);
  const [scores, setScores] = useState<ScoreDistribution | null>(null);

  const [funnelLoading, setFunnelLoading] = useState(true);
  const [channelLoading, setChannelLoading] = useState(true);
  const [timelineLoading, setTimelineLoading] = useState(true);
  const [scoresLoading, setScoresLoading] = useState(true);

  const [funnelError, setFunnelError] = useState<string | null>(null);
  const [channelError, setChannelError] = useState<string | null>(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [scoresError, setScoresError] = useState<string | null>(null);

  const loadFunnel = useCallback(async () => {
    setFunnelLoading(true);
    setFunnelError(null);
    try {
      const data = await fetchFunnel(days);
      setFunnel(data);
    } catch {
      setFunnelError("Failed to load funnel data");
    } finally {
      setFunnelLoading(false);
    }
  }, [days]);

  const loadChannel = useCallback(async () => {
    setChannelLoading(true);
    setChannelError(null);
    try {
      const data = await fetchChannelPerformance(days);
      setChannel(data);
    } catch {
      setChannelError("Failed to load channel data");
    } finally {
      setChannelLoading(false);
    }
  }, [days]);

  const loadTimeline = useCallback(async () => {
    setTimelineLoading(true);
    setTimelineError(null);
    try {
      const data = await fetchActivityTimeline(days, "day");
      setTimeline(data);
    } catch {
      setTimelineError("Failed to load activity timeline");
    } finally {
      setTimelineLoading(false);
    }
  }, [days]);

  const loadScores = useCallback(async () => {
    setScoresLoading(true);
    setScoresError(null);
    try {
      const data = await fetchScoreDistribution();
      setScores(data);
    } catch {
      setScoresError("Failed to load score distribution");
    } finally {
      setScoresLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFunnel();
    loadChannel();
    loadTimeline();
  }, [loadFunnel, loadChannel, loadTimeline]);

  useEffect(() => {
    loadScores();
  }, [loadScores]);

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>
          <p className="text-sm text-gray-400 mt-1">
            Outreach funnel, channel performance, and match quality
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 focus:border-indigo-500 focus:outline-none"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      <div className="space-y-6">
        {/* Section 1: Outreach Funnel */}
        {funnelLoading ? (
          <CardSkeleton />
        ) : funnelError ? (
          <ErrorCard message={funnelError} onRetry={loadFunnel} />
        ) : (
          <FunnelCard data={funnel} />
        )}

        {/* Section 2: Channel Performance */}
        {channelLoading ? (
          <CardSkeleton />
        ) : channelError ? (
          <ErrorCard message={channelError} onRetry={loadChannel} />
        ) : (
          <ChannelCard data={channel} />
        )}

        {/* Section 3: Activity Timeline */}
        {timelineLoading ? (
          <CardSkeleton />
        ) : timelineError ? (
          <ErrorCard message={timelineError} onRetry={loadTimeline} />
        ) : (
          <TimelineCard data={timeline} />
        )}

        {/* Section 4: Score Distribution */}
        {scoresLoading ? (
          <CardSkeleton />
        ) : scoresError ? (
          <ErrorCard message={scoresError} onRetry={loadScores} />
        ) : (
          <ScoreCard data={scores} />
        )}
      </div>
    </div>
  );
}

// ── Section 1: Funnel ───────────────────────────────────────────────

function FunnelCard({ data }: { data: FunnelData | null }) {
  if (!data) return null;

  const maxCount = Math.max(...data.stages.map((s) => s.count), 1);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-gray-100">
          Outreach Funnel
        </h2>
        <span className="text-sm text-gray-400">
          {data.total_matches} total matches
        </span>
      </div>

      {data.total_matches === 0 ? (
        <p className="text-sm text-gray-500 py-4 text-center">
          No matches in this period. Run Scout to find opportunities.
        </p>
      ) : (
        <div className="space-y-3">
          {data.stages.map((stage, i) => {
            const widthPct = Math.max((stage.count / maxCount) * 100, 2);
            const opacity = 1 - i * 0.12;
            return (
              <div key={stage.stage} className="flex items-center gap-4">
                <span className="text-sm text-gray-400 w-24 text-right shrink-0">
                  {STAGE_LABELS[stage.stage] ?? stage.stage}
                </span>
                <div className="flex-1 relative">
                  <div
                    className="h-8 rounded-md flex items-center px-3 transition-all duration-500"
                    style={{
                      width: `${widthPct}%`,
                      backgroundColor: `rgba(99, 102, 241, ${opacity})`,
                      minWidth: "40px",
                    }}
                  >
                    <span className="text-xs font-bold text-white">
                      {stage.count}
                    </span>
                  </div>
                </div>
                {i > 0 && (
                  <span className="text-xs text-gray-500 w-14 text-right shrink-0">
                    {stage.conversion_rate}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {(data.closed_lost > 0 || data.paused > 0) && (
        <div className="flex gap-4 mt-4 pt-4 border-t border-gray-800">
          {data.closed_lost > 0 && (
            <span className="text-xs text-gray-500">
              Closed Lost: {data.closed_lost}
            </span>
          )}
          {data.paused > 0 && (
            <span className="text-xs text-gray-500">
              Paused: {data.paused}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Section 2: Channel Performance ──────────────────────────────────

function ChannelCard({ data }: { data: ChannelPerformance | null }) {
  if (!data) return null;

  const hasEmail = data.email.sent > 0;
  const hasCalls = data.call.attempted > 0;
  const noData = !hasEmail && !hasCalls;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-gray-100 mb-5">
        Channel Performance
      </h2>

      {noData ? (
        <p className="text-sm text-gray-500 py-4 text-center">
          No outreach activity in this period.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Email Card */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-4">
              <svg
                className="w-5 h-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                />
              </svg>
              <h3 className="text-sm font-semibold text-gray-200">Email</h3>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Sent</span>
                <span className="text-sm text-gray-200 font-medium">
                  {data.email.sent}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Opened</span>
                <span className="text-sm text-gray-200 font-medium">
                  {data.email.opened}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Replied</span>
                <span className="text-sm text-gray-200 font-medium">
                  {data.email.replied}
                </span>
              </div>
              <div className="pt-2 border-t border-gray-700">
                <div className="flex justify-between items-baseline">
                  <span className="text-sm text-gray-400">Open Rate</span>
                  <span
                    className={`text-2xl font-bold ${rateColor(data.email.open_rate)}`}
                  >
                    {data.email.open_rate}%
                  </span>
                </div>
                <div className="flex justify-between items-baseline mt-2">
                  <span className="text-sm text-gray-400">Reply Rate</span>
                  <span
                    className={`text-2xl font-bold ${rateColor(data.email.reply_rate)}`}
                  >
                    {data.email.reply_rate}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Call Card */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-4">
              <svg
                className="w-5 h-5 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"
                />
              </svg>
              <h3 className="text-sm font-semibold text-gray-200">Calls</h3>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Attempted</span>
                <span className="text-sm text-gray-200 font-medium">
                  {data.call.attempted}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Connected</span>
                <span className="text-sm text-gray-200 font-medium">
                  {data.call.connected}
                </span>
              </div>
              <div className="pt-2 border-t border-gray-700">
                <div className="flex justify-between items-baseline">
                  <span className="text-sm text-gray-400">Connect Rate</span>
                  <span
                    className={`text-3xl font-bold ${rateColor(data.call.rate)}`}
                  >
                    {data.call.rate}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Section 3: Activity Timeline ────────────────────────────────────

function TimelineCard({ data }: { data: ActivityTimeline | null }) {
  if (!data) return null;

  const entries = data.timeline;
  const noData = entries.length === 0;

  const maxVal = noData
    ? 1
    : Math.max(
        ...entries.map((e) =>
          Math.max(e.matches_found, e.emails_sent, e.calls_made),
        ),
        1,
      );

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-gray-100 mb-5">
        Activity Timeline
      </h2>

      {noData ? (
        <p className="text-sm text-gray-500 py-4 text-center">
          No activity recorded in this period.
        </p>
      ) : (
        <>
          {/* Legend */}
          <div className="flex gap-5 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-indigo-500" />
              <span className="text-xs text-gray-400">Matches</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-emerald-500" />
              <span className="text-xs text-gray-400">Emails</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-amber-500" />
              <span className="text-xs text-gray-400">Calls</span>
            </div>
          </div>

          {/* Chart */}
          <div className="flex items-end gap-1 h-40 overflow-x-auto pb-6 relative">
            {entries.map((entry) => {
              const matchH = (entry.matches_found / maxVal) * 100;
              const emailH = (entry.emails_sent / maxVal) * 100;
              const callH = (entry.calls_made / maxVal) * 100;
              const dateLabel = new Date(entry.date).toLocaleDateString(
                "en-US",
                { month: "short", day: "numeric" },
              );
              const total =
                entry.matches_found + entry.emails_sent + entry.calls_made;

              return (
                <div
                  key={entry.date}
                  className="flex flex-col items-center flex-1 min-w-[24px] group relative"
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-800 border border-gray-700 rounded-lg p-2 text-xs whitespace-nowrap shadow-lg">
                      <p className="text-gray-300 font-medium mb-1">
                        {dateLabel}
                      </p>
                      <p className="text-indigo-400">
                        Matches: {entry.matches_found}
                      </p>
                      <p className="text-emerald-400">
                        Emails: {entry.emails_sent}
                      </p>
                      <p className="text-amber-400">
                        Calls: {entry.calls_made}
                      </p>
                    </div>
                  </div>

                  {/* Bars */}
                  <div className="flex gap-px items-end h-full">
                    {total === 0 ? (
                      <div className="w-1.5 h-0.5 bg-gray-700 rounded-t" />
                    ) : (
                      <>
                        <div
                          className="w-1.5 bg-indigo-500 rounded-t transition-all duration-300"
                          style={{
                            height: `${Math.max(matchH, 2)}%`,
                          }}
                        />
                        <div
                          className="w-1.5 bg-emerald-500 rounded-t transition-all duration-300"
                          style={{
                            height: `${Math.max(emailH, 2)}%`,
                          }}
                        />
                        <div
                          className="w-1.5 bg-amber-500 rounded-t transition-all duration-300"
                          style={{
                            height: `${Math.max(callH, 2)}%`,
                          }}
                        />
                      </>
                    )}
                  </div>

                  {/* Date label (show subset to avoid crowding) */}
                  {entries.length <= 14 && (
                    <span className="text-[9px] text-gray-600 mt-1 absolute -bottom-5 whitespace-nowrap">
                      {dateLabel}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Show start/end dates if too many entries */}
          {entries.length > 14 && (
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-gray-600">
                {new Date(entries[0].date).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </span>
              <span className="text-[10px] text-gray-600">
                {new Date(
                  entries[entries.length - 1].date,
                ).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Section 4: Score Distribution ───────────────────────────────────

function ScoreCard({ data }: { data: ScoreDistribution | null }) {
  if (!data) return null;

  const maxCount = Math.max(...data.buckets.map((b) => b.count), 1);
  const totalMatches = data.buckets.reduce((sum, b) => sum + b.count, 0);
  const noData = totalMatches === 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-gray-100">
          Match Quality Distribution
        </h2>
        <span className="text-sm text-gray-400">
          {totalMatches} matches scored
        </span>
      </div>

      {noData ? (
        <p className="text-sm text-gray-500 py-4 text-center">
          No scored matches yet. Run Scout to score opportunities.
        </p>
      ) : (
        <div className="flex items-end gap-2 h-32">
          {data.buckets.map((bucket) => {
            const heightPct = (bucket.count / maxCount) * 100;
            return (
              <div
                key={bucket.bucket}
                className="flex flex-col items-center flex-1 group relative"
              >
                {/* Tooltip */}
                <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                  <div className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs whitespace-nowrap shadow-lg">
                    <span className="text-gray-300">
                      Score {bucket.bucket}: {bucket.count} matches
                    </span>
                  </div>
                </div>

                {/* Count label */}
                {bucket.count > 0 && (
                  <span className="text-[10px] text-gray-500 mb-1">
                    {bucket.count}
                  </span>
                )}

                {/* Bar */}
                <div
                  className={`w-full rounded-t transition-all duration-300 ${bucketColor(bucket.bucket)}`}
                  style={{
                    height: `${Math.max(heightPct, bucket.count > 0 ? 4 : 1)}%`,
                    opacity: bucket.count > 0 ? 1 : 0.2,
                  }}
                />

                {/* Label */}
                <span className="text-[9px] text-gray-600 mt-1">
                  {bucket.bucket}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {!noData && (
        <div className="flex gap-5 mt-4 pt-3 border-t border-gray-800">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-red-500" />
            <span className="text-xs text-gray-500">Low (&lt;30)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-amber-500" />
            <span className="text-xs text-gray-500">Medium (30-60)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
            <span className="text-xs text-gray-500">High (&gt;60)</span>
          </div>
        </div>
      )}
    </div>
  );
}
