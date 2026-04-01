import GlassCard from "@/components/ui/GlassCard";

interface SynthesizeSectionProps {
  findingsCount: number;
  synthesizing: boolean;
  synthesizeSuccess: boolean;
  onSynthesize: () => void;
  suggestedMissions: string[];
  isDone: boolean;
  onSuggestionClick: (suggestion: string) => void;
}

export default function SynthesizeSection({
  findingsCount,
  synthesizing,
  synthesizeSuccess,
  onSynthesize,
  suggestedMissions,
  isDone,
  onSuggestionClick,
}: SynthesizeSectionProps) {
  return (
    <>
      {/* ── Synthesize Report CTA ──────────────────────────────────── */}
      <GlassCard className="border-emerald-500/30 p-8 text-center">
        {synthesizeSuccess ? (
          <div className="stream-in">
            <div className="text-emerald-400 text-lg font-semibold mb-2">
              Report generated successfully
            </div>
            <p className="text-sm text-gray-400">Redirecting to your report...</p>
          </div>
        ) : (
          <>
            <h3 className="text-lg font-semibold text-white mb-2">
              Mission Complete
            </h3>
            <p className="text-sm text-gray-400 mb-6 max-w-md mx-auto">
              {findingsCount} findings collected. Structure them into a comprehensive synthesized report.
            </p>
            <button
              onClick={onSynthesize}
              disabled={synthesizing}
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 hover:border-emerald-400/50 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-semibold transition-all duration-[180ms]"
            >
              {synthesizing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-emerald-400/30 border-t-emerald-400" />
                  Synthesizing...
                </>
              ) : (
                "Structure Findings into Synthesized Report"
              )}
            </button>
          </>
        )}
      </GlassCard>

      {/* ── Continue Research (Suggested Missions) ──────────────────── */}
      {isDone && suggestedMissions.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xs font-semibold text-gray-500 tracking-widest uppercase">
            Continue Research
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestedMissions.map((suggestion, idx) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick(suggestion)}
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
    </>
  );
}
