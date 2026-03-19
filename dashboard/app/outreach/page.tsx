"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import type {
  Contact,
  Campaign,
  Match,
  ResearchResult,
  AutopilotStatus,
} from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tab = "networking" | "outreach" | "conversations" | "ideas";

const TABS: { key: Tab; label: string; desc: string; icon: string }[] = [
  {
    key: "networking",
    label: "Networking",
    desc: "Contacts grouped by company",
    icon: "M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z",
  },
  {
    key: "outreach",
    label: "Cold Outreach",
    desc: "Multi-channel campaigns",
    icon: "M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5",
  },
  {
    key: "conversations",
    label: "Conversations",
    desc: "Active campaign timelines",
    icon: "M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155",
  },
  {
    key: "ideas",
    label: "Ideas",
    desc: "AI research & autopilot",
    icon: "M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
  },
];

const SOURCE_COLORS: Record<string, string> = {
  exa: "bg-purple-500/15 text-purple-400 border-purple-500/25",
  openclaw: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  manual: "bg-gray-500/15 text-gray-400 border-gray-500/25",
};

// ---------------------------------------------------------------------------
// Toast component
// ---------------------------------------------------------------------------
function Toast({
  message,
  type,
  onClose,
}: {
  message: string;
  type: "success" | "error" | "info";
  onClose: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg =
    type === "success"
      ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
      : type === "error"
        ? "bg-red-500/15 border-red-500/30 text-red-400"
        : "bg-blue-500/15 border-blue-500/30 text-blue-400";

  return (
    <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-xl border text-sm font-medium shadow-lg ${bg}`}>
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------
function Spinner({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <div
      className={`border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin ${className}`}
    />
  );
}

// ---------------------------------------------------------------------------
// Channel status indicator dot
// ---------------------------------------------------------------------------
function ChannelDot({
  status,
  channel,
}: {
  status: "sent" | "draft" | "completed" | "pending" | "none" | "failed";
  channel: "email" | "call" | "linkedin";
}) {
  const channelColors: Record<string, Record<string, string>> = {
    email: {
      sent: "bg-blue-400",
      draft: "bg-blue-400/40",
      none: "bg-gray-600",
      pending: "bg-gray-500",
      failed: "bg-red-400",
      completed: "bg-blue-400",
    },
    call: {
      completed: "bg-emerald-400",
      pending: "bg-gray-500",
      none: "bg-gray-600",
      sent: "bg-emerald-400",
      draft: "bg-emerald-400/40",
      failed: "bg-red-400",
    },
    linkedin: {
      sent: "bg-purple-400",
      draft: "bg-purple-400/40",
      none: "bg-gray-600",
      pending: "bg-gray-500",
      failed: "bg-red-400",
      completed: "bg-purple-400",
    },
  };

  const labels: Record<string, string> = {
    email: "Email",
    call: "Call",
    linkedin: "LinkedIn",
  };

  const bg = channelColors[channel]?.[status] ?? "bg-gray-600";

  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${bg}`} />
      <span className="text-[10px] text-gray-500">{labels[channel]}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function OutreachPage() {
  const [tab, setTab] = useState<Tab>("networking");
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);

  // Networking form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [contactForm, setContactForm] = useState({
    company: "",
    name: "",
    title: "",
    phone: "",
    email: "",
  });
  const [savingContact, setSavingContact] = useState(false);

  // Research state
  const [researchResults, setResearchResults] = useState<
    Record<string, ResearchResult>
  >({});
  const [researchLoading, setResearchLoading] = useState<
    Record<string, boolean>
  >({});

  // Autopilot state
  const [autopilotStatus, setAutopilotStatus] =
    useState<AutopilotStatus | null>(null);
  const [autopilotRunning, setAutopilotRunning] = useState(false);

  // Campaign expanded state
  const [expandedCampaigns, setExpandedCampaigns] = useState<
    Record<string, string | null>
  >({});

  // Email editing state
  const [editingEmails, setEditingEmails] = useState<Record<string, string>>(
    {}
  );

  // Action loading states
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>(
    {}
  );

  // Create campaign form
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [newCampaignMatch, setNewCampaignMatch] = useState("");
  const [newCampaignContact, setNewCampaignContact] = useState("");

  // -----------------------------------------------------------------------
  // Data loading
  // -----------------------------------------------------------------------
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [contactsRes, campaignsRes, matchesRes] = await Promise.all([
        fetch(`${API}/contacts`).then((r) => r.json()),
        fetch(`${API}/campaigns`).then((r) => r.json()),
        fetch(`${API}/matches?limit=50`).then((r) => r.json()),
      ]);
      setContacts(contactsRes.items ?? []);
      setCampaigns(campaignsRes.items ?? []);
      setMatches(
        (matchesRes.items ?? []).filter(
          (m: Match) => m.composite_score > 0
        )
      );
    } catch {
      setToast({ message: "Failed to load data", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAutopilotStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/autopilot/status`);
      if (res.ok) {
        const data = await res.json();
        setAutopilotStatus(data);
      }
    } catch {
      // Autopilot may not be configured yet
    }
  }, []);

  useEffect(() => {
    loadData();
    loadAutopilotStatus();
  }, [loadData, loadAutopilotStatus]);

  // -----------------------------------------------------------------------
  // Contacts grouped by company
  // -----------------------------------------------------------------------
  const contactsByCompany = useMemo(() => {
    const groups: Record<string, Contact[]> = {};
    for (const c of contacts) {
      const key = c.company || "Unknown";
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key] = [...groups[key], c];
    }
    return groups;
  }, [contacts]);

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------
  async function addContact(e: React.FormEvent) {
    e.preventDefault();
    if (!contactForm.company.trim()) return;
    setSavingContact(true);
    try {
      const res = await fetch(`${API}/contacts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm),
      });
      if (res.ok) {
        const newContact = await res.json();
        setContacts((prev) => [newContact, ...prev]);
        setContactForm({ company: "", name: "", title: "", phone: "", email: "" });
        setShowAddForm(false);
        setToast({ message: "Contact added", type: "success" });
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed" }));
        setToast({
          message: err.detail || "Failed to add contact",
          type: "error",
        });
      }
    } catch {
      setToast({ message: "Network error", type: "error" });
    } finally {
      setSavingContact(false);
    }
  }

  async function removeContact(id: string) {
    try {
      await fetch(`${API}/contacts/${id}`, { method: "DELETE" });
      setContacts((prev) => prev.filter((c) => c.id !== id));
      setToast({ message: "Contact removed", type: "info" });
    } catch {
      setToast({ message: "Failed to remove contact", type: "error" });
    }
  }

  async function handleResearch(matchId: string) {
    setResearchLoading((prev) => ({ ...prev, [matchId]: true }));
    try {
      const res = await fetch(`${API}/research/${matchId}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setResearchResults((prev) => ({ ...prev, [matchId]: data }));
        setToast({ message: "Research complete", type: "success" });
      } else {
        setToast({ message: "Research failed", type: "error" });
      }
    } catch {
      setToast({ message: "Research request failed", type: "error" });
    } finally {
      setResearchLoading((prev) => ({ ...prev, [matchId]: false }));
    }
  }

  // fetchResearch can be called to load existing research results
  void (async function _prefetchResearch() {
    for (const m of matches.slice(0, 5)) {
      try {
        const res = await fetch(`${API}/research/${m.id}`);
        if (res.ok) {
          const data = await res.json();
          setResearchResults((prev) => ({ ...prev, [m.id]: data }));
        }
      } catch { /* ignore */ }
    }
  });

  async function handleRunAutopilot() {
    setAutopilotRunning(true);
    try {
      const res = await fetch(`${API}/autopilot/run`, { method: "POST" });
      if (res.ok) {
        setToast({ message: "Autopilot cycle complete", type: "success" });
        loadAutopilotStatus();
        loadData();
      } else {
        setToast({ message: "Autopilot run failed", type: "error" });
      }
    } catch {
      setToast({ message: "Autopilot request failed", type: "error" });
    } finally {
      setAutopilotRunning(false);
    }
  }

  async function createCampaign() {
    if (!newCampaignMatch || !newCampaignContact) return;
    setActionLoading((prev) => ({ ...prev, createCampaign: true }));
    try {
      const res = await fetch(`${API}/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          match_id: newCampaignMatch,
          contact_id: newCampaignContact,
        }),
      });
      if (res.ok) {
        const campaign = await res.json();
        setCampaigns((prev) => [campaign, ...prev]);
        setShowCreateCampaign(false);
        setNewCampaignMatch("");
        setNewCampaignContact("");
        setToast({ message: "Campaign created", type: "success" });
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed" }));
        setToast({
          message: err.detail || "Failed to create campaign",
          type: "error",
        });
      }
    } catch {
      setToast({ message: "Network error", type: "error" });
    } finally {
      setActionLoading((prev) => ({ ...prev, createCampaign: false }));
    }
  }

  async function handleCallNow(campaignId: string) {
    setActionLoading((prev) => ({ ...prev, [`call_${campaignId}`]: true }));
    try {
      const res = await fetch(`${API}/campaigns/${campaignId}/call-now`, {
        method: "POST",
      });
      if (res.ok) {
        const updated = await res.json();
        setCampaigns((prev) =>
          prev.map((c) => (c.id === campaignId ? updated : c))
        );
        setToast({ message: "Call initiated", type: "success" });
      } else {
        const err = await res.json().catch(() => ({ detail: "Call failed" }));
        setToast({
          message: err.detail || "Call failed",
          type: "error",
        });
      }
    } catch {
      setToast({ message: "Network error", type: "error" });
    } finally {
      setActionLoading((prev) => ({ ...prev, [`call_${campaignId}`]: false }));
    }
  }

  async function handleSendEmail(campaignId: string) {
    setActionLoading((prev) => ({ ...prev, [`email_${campaignId}`]: true }));
    try {
      const res = await fetch(`${API}/campaigns/${campaignId}/send-email`, {
        method: "POST",
      });
      if (res.ok) {
        const updated = await res.json();
        setCampaigns((prev) =>
          prev.map((c) => (c.id === campaignId ? updated : c))
        );
        setToast({ message: "Email sent", type: "success" });
      } else {
        setToast({ message: "Failed to send email", type: "error" });
      }
    } catch {
      setToast({ message: "Network error", type: "error" });
    } finally {
      setActionLoading((prev) => ({
        ...prev,
        [`email_${campaignId}`]: false,
      }));
    }
  }

  async function handleGenerateOutreach(campaignId: string) {
    setActionLoading((prev) => ({
      ...prev,
      [`outreach_${campaignId}`]: true,
    }));
    try {
      const res = await fetch(
        `${API}/campaigns/${campaignId}/outreach-package`,
        { method: "POST" }
      );
      if (res.ok) {
        const updated = await res.json();
        setCampaigns((prev) =>
          prev.map((c) => (c.id === campaignId ? updated : c))
        );
        setToast({ message: "Outreach package generated", type: "success" });
      } else {
        setToast({ message: "Failed to generate outreach", type: "error" });
      }
    } catch {
      setToast({ message: "Network error", type: "error" });
    } finally {
      setActionLoading((prev) => ({
        ...prev,
        [`outreach_${campaignId}`]: false,
      }));
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setToast({ message: "Copied to clipboard", type: "info" });
  }

  function toggleCampaignSection(campaignId: string, section: string) {
    setExpandedCampaigns((prev) => ({
      ...prev,
      [campaignId]: prev[campaignId] === section ? null : section,
    }));
  }

  function getEmailStatus(
    campaign: Campaign
  ): "sent" | "draft" | "none" {
    if (campaign.status === "completed" && campaign.email_draft)
      return "sent";
    if (campaign.email_draft) return "draft";
    return "none";
  }

  function getCallStatus(
    campaign: Campaign
  ): "completed" | "pending" | "none" | "failed" {
    if (campaign.status === "completed") return "completed";
    if (campaign.status === "failed") return "failed";
    if (campaign.attempt_count > 0) return "pending";
    return "none";
  }

  function getLinkedinStatus(
    campaign: Campaign
  ): "sent" | "draft" | "none" {
    if (campaign.linkedin_msg) return "draft";
    return "none";
  }

  // -----------------------------------------------------------------------
  // Loading state
  // -----------------------------------------------------------------------
  if (loading) {
    return (
      <div className="max-w-6xl">
        <div className="text-center py-16">
          <Spinner className="w-8 h-8 mx-auto" />
          <p className="text-sm text-gray-500 mt-4">Loading outreach data...</p>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="max-w-6xl">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Outreach</h1>
        <p className="text-sm text-gray-400 mt-1">
          Multi-channel outreach: networking, cold email, calls, and LinkedIn
        </p>
      </div>

      {/* Tab bar */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`p-3 rounded-xl text-left transition-all border flex items-start gap-3 ${
              tab === t.key
                ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400"
                : "bg-gray-900 border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-300"
            }`}
          >
            <svg
              className={`w-5 h-5 mt-0.5 shrink-0 ${tab === t.key ? "text-indigo-400" : "text-gray-600"}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d={t.icon}
              />
            </svg>
            <div>
              <div className="text-sm font-semibold">{t.label}</div>
              <div className="text-[10px] mt-0.5 opacity-70">{t.desc}</div>
            </div>
          </button>
        ))}
      </div>

      {/* ================================================================= */}
      {/* NETWORKING TAB                                                     */}
      {/* ================================================================= */}
      {tab === "networking" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-200">
              Contacts ({contacts.length})
            </h2>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors"
            >
              {showAddForm ? "Cancel" : "+ Add Contact"}
            </button>
          </div>

          {/* Add contact form */}
          {showAddForm && (
            <form
              onSubmit={addContact}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-5"
            >
              <h3 className="text-sm font-medium text-gray-300 mb-3">
                New Contact
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <input
                  value={contactForm.company}
                  onChange={(e) =>
                    setContactForm({ ...contactForm, company: e.target.value })
                  }
                  placeholder="Company *"
                  required
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
                <input
                  value={contactForm.name}
                  onChange={(e) =>
                    setContactForm({ ...contactForm, name: e.target.value })
                  }
                  placeholder="Name"
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
                <input
                  value={contactForm.title}
                  onChange={(e) =>
                    setContactForm({ ...contactForm, title: e.target.value })
                  }
                  placeholder="Title (e.g. Engineering Manager)"
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
                <input
                  value={contactForm.phone}
                  onChange={(e) =>
                    setContactForm({ ...contactForm, phone: e.target.value })
                  }
                  placeholder="Phone (+1...)"
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                />
                <input
                  value={contactForm.email}
                  onChange={(e) =>
                    setContactForm({ ...contactForm, email: e.target.value })
                  }
                  placeholder="Email"
                  type="email"
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none col-span-2"
                />
              </div>
              <button
                type="submit"
                disabled={savingContact || !contactForm.company.trim()}
                className="mt-3 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {savingContact && <Spinner className="w-4 h-4" />}
                {savingContact ? "Saving..." : "Save Contact"}
              </button>
            </form>
          )}

          {/* Contacts grouped by company */}
          {Object.keys(contactsByCompany).length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <svg
                className="w-10 h-10 mx-auto text-gray-700 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
                />
              </svg>
              <p className="text-sm text-gray-500">No contacts yet.</p>
              <p className="text-xs text-gray-600 mt-1">
                Add people you want to reach out to.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {Object.entries(contactsByCompany).map(
                ([company, companyContacts]) => {
                  // Find a match for this company to enable research
                  const companyMatch = matches.find(
                    (m) =>
                      m.opportunity?.company?.toLowerCase() ===
                      company.toLowerCase()
                  );

                  return (
                    <div
                      key={company}
                      className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
                    >
                      {/* Company header */}
                      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/80">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center">
                            <span className="text-xs font-bold text-indigo-400">
                              {company.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-gray-200">
                              {company}
                            </h3>
                            <p className="text-[10px] text-gray-500">
                              {companyContacts.length} contact
                              {companyContacts.length !== 1 ? "s" : ""}
                            </p>
                          </div>
                        </div>
                        {companyMatch && (
                          <button
                            onClick={() => handleResearch(companyMatch.id)}
                            disabled={
                              researchLoading[companyMatch.id] ?? false
                            }
                            className="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 border border-purple-500/20"
                          >
                            {researchLoading[companyMatch.id] ? (
                              <>
                                <Spinner className="w-3 h-3" />
                                Researching...
                              </>
                            ) : (
                              <>
                                <svg
                                  className="w-3.5 h-3.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  strokeWidth={2}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                                  />
                                </svg>
                                Research {company}
                              </>
                            )}
                          </button>
                        )}
                      </div>

                      {/* Contact rows */}
                      <div className="divide-y divide-gray-800/50">
                        {companyContacts.map((c) => (
                          <div
                            key={c.id}
                            className="px-5 py-3 flex items-center justify-between hover:bg-gray-800/30 transition-colors"
                          >
                            <div className="flex items-center gap-4 min-w-0">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-100 truncate">
                                    {c.name || "Unnamed"}
                                  </span>
                                  {c.title && (
                                    <span className="text-xs text-gray-500 truncate">
                                      {c.title}
                                    </span>
                                  )}
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[9px] font-medium uppercase border ${
                                      SOURCE_COLORS[c.source] ??
                                      SOURCE_COLORS.manual
                                    }`}
                                  >
                                    {c.source}
                                  </span>
                                </div>
                                <div className="flex items-center gap-3 mt-0.5">
                                  {c.phone && (
                                    <span className="text-xs text-gray-500 font-mono">
                                      {c.phone}
                                    </span>
                                  )}
                                  {c.email && (
                                    <span className="text-xs text-gray-500">
                                      {c.email}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <button
                              onClick={() => removeContact(c.id)}
                              className="text-xs text-red-400/40 hover:text-red-400 transition-colors shrink-0 ml-4"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* COLD OUTREACH TAB                                                  */}
      {/* ================================================================= */}
      {tab === "outreach" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-200">
              Campaigns ({campaigns.length})
            </h2>
            <button
              onClick={() => setShowCreateCampaign(!showCreateCampaign)}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors"
            >
              {showCreateCampaign ? "Cancel" : "+ New Campaign"}
            </button>
          </div>

          {/* Create campaign form */}
          {showCreateCampaign && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-5">
              <h3 className="text-sm font-medium text-gray-300 mb-3">
                Create Campaign
              </h3>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Match / Opportunity
                  </label>
                  <select
                    value={newCampaignMatch}
                    onChange={(e) => setNewCampaignMatch(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="">Select a match...</option>
                    {matches.slice(0, 20).map((m) => (
                      <option key={m.id} value={m.id}>
                        {Math.round(m.composite_score)} -{" "}
                        {m.opportunity?.title} at {m.opportunity?.company}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Contact
                  </label>
                  <select
                    value={newCampaignContact}
                    onChange={(e) => setNewCampaignContact(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="">Select a contact...</option>
                    {contacts.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name || c.company} - {c.company}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={createCampaign}
                disabled={
                  !newCampaignMatch ||
                  !newCampaignContact ||
                  actionLoading.createCampaign
                }
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {actionLoading.createCampaign && (
                  <Spinner className="w-4 h-4" />
                )}
                {actionLoading.createCampaign
                  ? "Creating..."
                  : "Create Campaign"}
              </button>
            </div>
          )}

          {campaigns.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <svg
                className="w-10 h-10 mx-auto text-gray-700 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                />
              </svg>
              <p className="text-sm text-gray-500">No campaigns yet.</p>
              <p className="text-xs text-gray-600 mt-1">
                Create one by selecting a match and a contact above.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {campaigns.map((camp) => {
                const company =
                  camp.match?.opportunity?.company ?? "Unknown Company";
                const role =
                  camp.match?.opportunity?.title ?? "Unknown Position";
                const contactName = camp.contact?.name ?? "Unknown";
                const contactPhone = camp.contact?.phone ?? "";
                const emailStatus = getEmailStatus(camp);
                const callStatus = getCallStatus(camp);
                const linkedinStatus = getLinkedinStatus(camp);
                const expanded = expandedCampaigns[camp.id];

                return (
                  <div
                    key={camp.id}
                    className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
                  >
                    {/* Campaign header */}
                    <div className="p-5">
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="min-w-0">
                          <Link
                            href={`/calls/${camp.id}`}
                            className="text-base font-semibold text-gray-100 hover:text-indigo-400 transition-colors"
                          >
                            {role}
                          </Link>
                          <p className="text-sm text-gray-400 mt-0.5">
                            {company}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {camp.match?.composite_score != null && (
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-bold ${
                                camp.match.composite_score >= 70
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : camp.match.composite_score >= 40
                                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                    : "bg-red-500/10 text-red-400 border border-red-500/20"
                              }`}
                            >
                              {Math.round(camp.match.composite_score)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Contact + channel indicators */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <svg
                            className="w-4 h-4 text-gray-500"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={1.5}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                            />
                          </svg>
                          <span>{contactName}</span>
                          {contactPhone && (
                            <span className="text-xs text-gray-500 font-mono">
                              {contactPhone}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          <ChannelDot
                            channel="email"
                            status={emailStatus}
                          />
                          <ChannelDot
                            channel="call"
                            status={callStatus}
                          />
                          <ChannelDot
                            channel="linkedin"
                            status={linkedinStatus}
                          />
                        </div>
                      </div>

                      {/* Section toggle buttons */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          onClick={() =>
                            toggleCampaignSection(camp.id, "email")
                          }
                          className={`px-2.5 py-1 text-xs rounded-lg border transition-colors ${
                            expanded === "email"
                              ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
                              : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300"
                          }`}
                        >
                          Email Draft
                        </button>
                        <button
                          onClick={() =>
                            toggleCampaignSection(camp.id, "script")
                          }
                          className={`px-2.5 py-1 text-xs rounded-lg border transition-colors ${
                            expanded === "script"
                              ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                              : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300"
                          }`}
                        >
                          Call Script
                        </button>
                        <button
                          onClick={() =>
                            toggleCampaignSection(camp.id, "linkedin")
                          }
                          className={`px-2.5 py-1 text-xs rounded-lg border transition-colors ${
                            expanded === "linkedin"
                              ? "bg-purple-500/15 border-purple-500/30 text-purple-400"
                              : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300"
                          }`}
                        >
                          LinkedIn
                        </button>

                        <div className="flex-1" />

                        {/* Generate all channels */}
                        {!camp.email_draft &&
                          !camp.linkedin_msg &&
                          !camp.script_json && (
                            <button
                              onClick={() =>
                                handleGenerateOutreach(camp.id)
                              }
                              disabled={
                                actionLoading[`outreach_${camp.id}`]
                              }
                              className="px-3 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 border border-indigo-500/20"
                            >
                              {actionLoading[`outreach_${camp.id}`] ? (
                                <>
                                  <Spinner className="w-3 h-3" />
                                  Generating...
                                </>
                              ) : (
                                "Generate All Channels"
                              )}
                            </button>
                          )}
                      </div>
                    </div>

                    {/* Expanded email section */}
                    {expanded === "email" && (
                      <div className="border-t border-gray-800 p-5 bg-gray-950/50">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-xs font-medium text-blue-400 uppercase tracking-wider">
                            Email Draft
                          </h4>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleSendEmail(camp.id)}
                              disabled={
                                actionLoading[`email_${camp.id}`] ||
                                !camp.email_draft
                              }
                              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                              {actionLoading[`email_${camp.id}`] ? (
                                <>
                                  <Spinner className="w-3 h-3" />
                                  Sending...
                                </>
                              ) : (
                                "Send Email"
                              )}
                            </button>
                          </div>
                        </div>
                        {camp.email_subject && (
                          <div className="mb-2">
                            <span className="text-[10px] text-gray-500 uppercase">
                              Subject:
                            </span>
                            <p className="text-sm text-gray-300">
                              {camp.email_subject}
                            </p>
                          </div>
                        )}
                        <textarea
                          value={
                            editingEmails[camp.id] ??
                            camp.email_draft ??
                            ""
                          }
                          onChange={(e) =>
                            setEditingEmails((prev) => ({
                              ...prev,
                              [camp.id]: e.target.value,
                            }))
                          }
                          placeholder="No email draft yet. Click 'Generate All Channels' to create one."
                          rows={6}
                          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none resize-none font-mono"
                        />
                      </div>
                    )}

                    {/* Expanded call script section */}
                    {expanded === "script" && (
                      <div className="border-t border-gray-800 p-5 bg-gray-950/50">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
                            Call Script
                          </h4>
                          <button
                            onClick={() => handleCallNow(camp.id)}
                            disabled={
                              actionLoading[`call_${camp.id}`] ||
                              (camp.status !== "pending" &&
                                camp.status !== "scheduled")
                            }
                            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
                          >
                            {actionLoading[`call_${camp.id}`] ? (
                              <>
                                <Spinner className="w-3 h-3" />
                                Calling...
                              </>
                            ) : (
                              <>
                                <svg
                                  className="w-3.5 h-3.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  strokeWidth={2}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"
                                  />
                                </svg>
                                Call Now
                              </>
                            )}
                          </button>
                        </div>
                        {camp.script_json &&
                        Object.keys(camp.script_json).length > 0 ? (
                          <div className="space-y-3">
                            {Object.entries(camp.script_json).map(
                              ([key, value]) => (
                                <div key={key}>
                                  <h5 className="text-xs font-medium text-gray-400 capitalize mb-1">
                                    {key.replace(/_/g, " ")}
                                  </h5>
                                  <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm text-gray-300">
                                    {typeof value === "string"
                                      ? value
                                      : Array.isArray(value)
                                        ? (value as string[]).map(
                                            (item, i) => (
                                              <div
                                                key={i}
                                                className="flex items-start gap-2 mb-1 last:mb-0"
                                              >
                                                <span className="text-indigo-400 mt-0.5">
                                                  &#8226;
                                                </span>
                                                <span>
                                                  {typeof item ===
                                                  "string"
                                                    ? item
                                                    : JSON.stringify(
                                                        item
                                                      )}
                                                </span>
                                              </div>
                                            )
                                          )
                                        : JSON.stringify(value, null, 2)}
                                  </div>
                                </div>
                              )
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-600">
                            No call script yet. Click &quot;Generate All
                            Channels&quot; to create one.
                          </p>
                        )}
                      </div>
                    )}

                    {/* Expanded linkedin section */}
                    {expanded === "linkedin" && (
                      <div className="border-t border-gray-800 p-5 bg-gray-950/50">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-xs font-medium text-purple-400 uppercase tracking-wider">
                            LinkedIn Message
                          </h4>
                          {camp.linkedin_msg && (
                            <button
                              onClick={() =>
                                copyToClipboard(camp.linkedin_msg!)
                              }
                              className="px-3 py-1 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-xs font-medium rounded-lg transition-colors border border-purple-500/20"
                            >
                              Copy LinkedIn
                            </button>
                          )}
                        </div>
                        {camp.linkedin_msg ? (
                          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm text-gray-300 whitespace-pre-wrap">
                            {camp.linkedin_msg}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-600">
                            No LinkedIn message yet. Click &quot;Generate
                            All Channels&quot; to create one.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* CONVERSATIONS TAB                                                  */}
      {/* ================================================================= */}
      {tab === "conversations" && (
        <div>
          <h2 className="text-lg font-semibold text-gray-200 mb-4">
            Active Conversations ({campaigns.filter((c) => c.attempt_count > 0).length})
          </h2>

          {campaigns.filter((c) => c.attempt_count > 0).length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <svg
                className="w-10 h-10 mx-auto text-gray-700 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"
                />
              </svg>
              <p className="text-sm text-gray-500">
                No active conversations yet.
              </p>
              <p className="text-xs text-gray-600 mt-1">
                Campaigns with call attempts or sent emails will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {campaigns
                .filter((c) => c.attempt_count > 0)
                .sort(
                  (a, b) =>
                    new Date(b.updated_at).getTime() -
                    new Date(a.updated_at).getTime()
                )
                .map((camp) => {
                  const company =
                    camp.match?.opportunity?.company ?? "Unknown";
                  const role =
                    camp.match?.opportunity?.title ?? "Unknown";
                  const contactName =
                    camp.contact?.name ?? "Unknown";
                  const isExpanded = expandedCampaigns[camp.id] === "timeline";

                  // Build timeline events
                  const events: {
                    type: string;
                    label: string;
                    time: string;
                    color: string;
                  }[] = [];

                  if (camp.email_draft) {
                    events.push({
                      type: "email",
                      label: "Email draft created",
                      time: camp.updated_at,
                      color: "blue",
                    });
                  }
                  if (camp.attempt_count > 0) {
                    events.push({
                      type: "call",
                      label: `Call attempted (${camp.attempt_count}/${camp.max_attempts})`,
                      time: camp.updated_at,
                      color: "emerald",
                    });
                  }
                  if (camp.linkedin_msg) {
                    events.push({
                      type: "linkedin",
                      label: "LinkedIn message drafted",
                      time: camp.updated_at,
                      color: "purple",
                    });
                  }

                  const outcomeMap: Record<string, string> = {
                    completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                    pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
                    in_progress: "bg-amber-500/10 text-amber-400 border-amber-500/20",
                    scheduled: "bg-blue-500/10 text-blue-400 border-blue-500/20",
                    failed: "bg-red-500/10 text-red-400 border-red-500/20",
                  };

                  return (
                    <div
                      key={camp.id}
                      className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
                    >
                      <div className="p-5">
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div>
                            <Link
                              href={`/calls/${camp.id}`}
                              className="text-sm font-semibold text-gray-100 hover:text-indigo-400 transition-colors"
                            >
                              {role} at {company}
                            </Link>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {contactName} -- {camp.attempt_count}/{camp.max_attempts} attempts
                            </p>
                          </div>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize ${
                              outcomeMap[camp.status] ??
                              outcomeMap.pending
                            }`}
                          >
                            {camp.status.replace(/_/g, " ")}
                          </span>
                        </div>

                        {/* Mini timeline */}
                        <div className="flex items-center gap-4 mb-3">
                          {events.map((ev, i) => (
                            <div key={i} className="flex items-center gap-1.5">
                              <div
                                className={`w-2 h-2 rounded-full bg-${ev.color}-400`}
                              />
                              <span className="text-[10px] text-gray-500">
                                {ev.label}
                              </span>
                            </div>
                          ))}
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              toggleCampaignSection(camp.id, "timeline")
                            }
                            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                          >
                            {isExpanded
                              ? "Hide timeline"
                              : "View full timeline"}
                          </button>
                          <div className="flex-1" />
                          <Link
                            href={`/calls/${camp.id}`}
                            className="text-xs text-gray-400 hover:text-gray-300 transition-colors"
                          >
                            Open details
                          </Link>
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="border-t border-gray-800 p-5 bg-gray-950/50">
                          <div className="relative pl-6">
                            <div className="absolute left-2 top-1 bottom-1 w-px bg-gray-800" />
                            {events.map((ev, i) => (
                              <div
                                key={i}
                                className="relative pb-4 last:pb-0"
                              >
                                <div
                                  className={`absolute left-[-16px] top-1 w-2.5 h-2.5 rounded-full border-2 border-gray-950 bg-${ev.color}-400`}
                                />
                                <div className="flex items-center gap-3">
                                  <span className="text-xs text-gray-500">
                                    {new Date(ev.time).toLocaleDateString()}
                                  </span>
                                  <span className="text-sm text-gray-300">
                                    {ev.label}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* IDEAS TAB                                                          */}
      {/* ================================================================= */}
      {tab === "ideas" && (
        <div>
          {/* Autopilot header */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-200">
                AI Research & Autopilot
              </h2>
              {autopilotStatus?.last_run && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Last autopilot run:{" "}
                  {new Date(autopilotStatus.last_run).toLocaleString()}
                </p>
              )}
            </div>
            <button
              onClick={handleRunAutopilot}
              disabled={autopilotRunning}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {autopilotRunning ? (
                <>
                  <Spinner className="w-4 h-4" />
                  Running Autopilot...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
                    />
                  </svg>
                  Run Autopilot
                </>
              )}
            </button>
          </div>

          {/* Autopilot status card */}
          {autopilotStatus?.last_result && (
            <div className="bg-purple-500/5 border border-purple-500/15 rounded-xl p-4 mb-5">
              <h3 className="text-xs font-medium text-purple-400 uppercase tracking-wider mb-2">
                Last Autopilot Run
              </h3>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(autopilotStatus.last_result).map(
                  ([key, value]) => (
                    <div key={key}>
                      <p className="text-[10px] text-gray-500 uppercase">
                        {key.replace(/_/g, " ")}
                      </p>
                      <p className="text-sm text-gray-300 font-medium">
                        {String(value)}
                      </p>
                    </div>
                  )
                )}
              </div>
            </div>
          )}

          {/* Top unresearched matches */}
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Top Matches for Research
          </h3>

          {matches.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-sm text-gray-500">
                No matches yet. Run Scout from the Profile page first.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {matches.slice(0, 10).map((m) => {
                const research = researchResults[m.id];
                const isResearching = researchLoading[m.id] ?? false;

                return (
                  <div
                    key={m.id}
                    className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
                  >
                    <div className="p-5">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              m.composite_score >= 70
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : m.composite_score >= 40
                                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                  : "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}
                          >
                            {Math.round(m.composite_score)}
                          </span>
                          <div>
                            <h4 className="text-sm font-semibold text-gray-100">
                              {m.opportunity?.title}
                            </h4>
                            <p className="text-xs text-indigo-400">
                              {m.opportunity?.company}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => {
                            if (research) {
                              // Toggle visibility by clearing
                              setResearchResults((prev) => {
                                const next = { ...prev };
                                delete next[m.id];
                                return next;
                              });
                            } else {
                              handleResearch(m.id);
                            }
                          }}
                          disabled={isResearching}
                          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {isResearching ? (
                            <>
                              <Spinner className="w-3 h-3" />
                              Researching...
                            </>
                          ) : research ? (
                            "Hide Research"
                          ) : (
                            <>
                              <svg
                                className="w-3.5 h-3.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                                />
                              </svg>
                              Deep Research
                            </>
                          )}
                        </button>
                      </div>

                      {m.rationale && (
                        <p className="text-xs text-gray-500 mt-2 line-clamp-2">
                          {m.rationale}
                        </p>
                      )}
                    </div>

                    {/* Research results */}
                    {research && (
                      <div className="border-t border-gray-800 bg-gray-950/50">
                        {/* Quality score */}
                        <div className="px-5 py-3 flex items-center gap-3 border-b border-gray-800/50">
                          <span className="text-[10px] text-gray-500 uppercase">
                            Research Quality:
                          </span>
                          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                research.quality_score >= 70
                                  ? "bg-emerald-400"
                                  : research.quality_score >= 40
                                    ? "bg-amber-400"
                                    : "bg-red-400"
                              }`}
                              style={{
                                width: `${Math.min(research.quality_score, 100)}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs text-gray-400 font-mono">
                            {research.quality_score}%
                          </span>
                        </div>

                        {/* Company intel */}
                        {Object.keys(research.company_intel).length > 0 && (
                          <div className="px-5 py-4 border-b border-gray-800/50">
                            <h5 className="text-xs font-medium text-indigo-400 uppercase tracking-wider mb-3">
                              Company Intelligence
                            </h5>
                            <div className="grid grid-cols-2 gap-3">
                              {Object.entries(research.company_intel).map(
                                ([key, value]) => (
                                  <div
                                    key={key}
                                    className="bg-gray-800/30 rounded-lg p-3"
                                  >
                                    <p className="text-[10px] text-gray-500 uppercase mb-1">
                                      {key.replace(/_/g, " ")}
                                    </p>
                                    <p className="text-xs text-gray-300">
                                      {typeof value === "string"
                                        ? value
                                        : JSON.stringify(value)}
                                    </p>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}

                        {/* Discovered contacts */}
                        {research.contacts_found.length > 0 && (
                          <div className="px-5 py-4 border-b border-gray-800/50">
                            <h5 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">
                              Discovered Contacts (
                              {research.contacts_found.length})
                            </h5>
                            <div className="space-y-2">
                              {research.contacts_found.map(
                                (contact, i) => (
                                  <div
                                    key={i}
                                    className="flex items-center justify-between bg-gray-800/30 rounded-lg p-3"
                                  >
                                    <div>
                                      <p className="text-sm text-gray-200">
                                        {String(
                                          contact.name || "Unknown"
                                        )}
                                      </p>
                                      <p className="text-xs text-gray-500">
                                        {String(contact.title || "")}{" "}
                                        {contact.email
                                          ? `-- ${String(contact.email)}`
                                          : ""}
                                      </p>
                                    </div>
                                    <button
                                      onClick={() => {
                                        setContactForm({
                                          company:
                                            m.opportunity?.company ?? "",
                                          name: String(
                                            contact.name || ""
                                          ),
                                          title: String(
                                            contact.title || ""
                                          ),
                                          phone: String(
                                            contact.phone || ""
                                          ),
                                          email: String(
                                            contact.email || ""
                                          ),
                                        });
                                        setTab("networking");
                                        setShowAddForm(true);
                                      }}
                                      className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs rounded-lg transition-colors border border-emerald-500/20"
                                    >
                                      Queue for Outreach
                                    </button>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}

                        {/* Sources */}
                        {research.sources_used.length > 0 && (
                          <div className="px-5 py-3">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[10px] text-gray-500 uppercase">
                                Sources:
                              </span>
                              {research.sources_used.map((src, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-400"
                                >
                                  {src}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
