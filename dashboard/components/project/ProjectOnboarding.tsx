"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  generateProjectQuestions,
  configureAndStartProject,
} from "@/lib/api";
import type { OnboardingQuestion } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { Project } from "@/lib/types";

interface ProjectOnboardingProps {
  project: Project;
}

export default function ProjectOnboarding({ project }: ProjectOnboardingProps) {
  const router = useRouter();
  const { toast } = useToast();

  const [questions, setQuestions] = useState<OnboardingQuestion[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [submitting, setSubmitting] = useState(false);
  const [questionsError, setQuestionsError] = useState(false);

  // Generate questions on mount
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await generateProjectQuestions(
          project.id,
          project.name,
          project.project_type,
        );
        if (!cancelled) {
          setQuestions(res.questions);
          const defaults: Record<string, string | string[]> = {};
          for (const q of res.questions) {
            defaults[q.id] = q.type === "multiselect" ? [] : "";
          }
          setAnswers(defaults);
        }
      } catch {
        if (!cancelled) {
          setQuestionsError(true);
          toast("Failed to generate onboarding questions", "error");
        }
      } finally {
        if (!cancelled) setLoadingQuestions(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [project.id, project.name, project.project_type, toast]);

  const updateAnswer = (questionId: string, value: string | string[]) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const toggleMultiselect = (questionId: string, option: string) => {
    setAnswers((prev) => {
      const current = (prev[questionId] as string[]) ?? [];
      const next = current.includes(option)
        ? current.filter((v) => v !== option)
        : [...current, option];
      return { ...prev, [questionId]: next };
    });
  };

  const allAnswered = questions.every((q) => {
    const val = answers[q.id];
    if (q.type === "multiselect") return (val as string[]).length > 0;
    return typeof val === "string" && val.trim().length > 0;
  });

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await configureAndStartProject(
        project.id,
        answers,
        project.name,
      );
      router.push(`/missions/${res.mission.id}`);
    } catch (e: unknown) {
      toast(
        e instanceof Error ? e.message : "Failed to start project",
        "error",
      );
      setSubmitting(false);
    }
  };

  if (loadingQuestions) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center pulse-glow">
        <div className="w-10 h-10 mx-auto mb-4 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
        </div>
        <p className="text-emerald-400 text-sm font-medium">
          Synthesizing
        </p>
      </div>
    );
  }

  if (questionsError) {
    return (
      <div className="glass-card rounded-2xl border border-gray-800/40 p-10 text-center">
        <p className="text-gray-400 text-sm">
          Could not generate questions. Try refreshing the page.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="glass-card rounded-2xl border border-gray-800/40 p-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">
          Project Setup
        </h2>
        <p className="text-gray-500 text-xs mb-6">
          Answer a few questions so the AI can tailor its research strategy.
        </p>

        <div className="space-y-6">
          {questions.map((q, idx) => (
            <div
              key={q.id}
              className="finding-reveal"
              style={{ animationDelay: `${idx * 80}ms` }}
            >
              <label htmlFor={q.id} className="block text-sm text-gray-200 mb-2">
                {q.question}
              </label>

              {q.type === "text" && (
                <input
                  id={q.id}
                  type="text"
                  value={(answers[q.id] as string) ?? ""}
                  onChange={(e) => updateAnswer(q.id, e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && allAnswered && !submitting && handleSubmit()}
                  placeholder={q.placeholder}
                  className="w-full glass-card rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 focus:ring-1 focus:ring-emerald-500/20 transition-all duration-[180ms]"
                />
              )}

              {q.type === "select" && q.options && (
                <div className="relative">
                  <select
                    id={q.id}
                    value={(answers[q.id] as string) ?? ""}
                    onChange={(e) => updateAnswer(q.id, e.target.value)}
                    className="w-full bg-[#0d1017] border border-white/[0.08] rounded-xl px-4 py-3 pr-10 text-sm text-gray-100 focus:outline-none focus:border-emerald-400/50 focus:ring-1 focus:ring-emerald-500/20 transition-all duration-[180ms] appearance-none cursor-pointer"
                  >
                    <option value="" disabled className="bg-[#0d1017] text-gray-500">
                      {q.placeholder}
                    </option>
                    {q.options.map((opt) => (
                      <option key={opt} value={opt} className="bg-[#0d1017] text-gray-100">
                        {opt}
                      </option>
                    ))}
                  </select>
                  <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              )}

              {q.type === "multiselect" && q.options && (
                <div className="flex flex-wrap gap-2">
                  {q.options.map((opt) => {
                    const selected = (
                      (answers[q.id] as string[]) ?? []
                    ).includes(opt);
                    return (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => toggleMultiselect(q.id, opt)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          selected
                            ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-300"
                            : "border-gray-700/50 bg-gray-900/40 text-gray-400 hover:border-gray-600"
                        }`}
                      >
                        {opt}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!allAnswered || submitting}
        className={`w-full py-4 rounded-2xl text-sm font-semibold transition-all duration-300 ${
          submitting
            ? "bg-emerald-600/80 text-white pulse-glow cursor-wait"
            : allAnswered
              ? "bg-emerald-600 hover:bg-emerald-500 text-white pulse-glow cursor-pointer"
              : "bg-gray-800 text-gray-500 cursor-not-allowed"
        }`}
      >
        {submitting ? (
          <span className="flex items-center justify-center gap-2.5">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Synthesizing context & launching agents...
          </span>
        ) : (
          "Context Synthesized \u2014 Start Research"
        )}
      </button>
    </div>
  );
}
