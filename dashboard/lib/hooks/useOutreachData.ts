"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import type {
  Contact,
  Campaign,
  Match,
  ResearchResult,
  AutopilotStatus,
} from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Tab = "networking" | "outreach" | "conversations" | "ideas";

export interface OutreachData {
  // Core data
  contacts: Contact[];
  campaigns: Campaign[];
  matches: Match[];
  loading: boolean;
  contactsByCompany: Record<string, Contact[]>;

  // Networking
  showAddForm: boolean;
  setShowAddForm: (v: boolean) => void;
  contactForm: ContactFormState;
  setContactForm: (v: ContactFormState) => void;
  savingContact: boolean;
  addContact: (e: React.FormEvent) => Promise<void>;
  removeContact: (id: string) => Promise<void>;

  // Campaigns
  showCreateCampaign: boolean;
  setShowCreateCampaign: (v: boolean) => void;
  newCampaignMatch: string;
  setNewCampaignMatch: (v: string) => void;
  newCampaignContact: string;
  setNewCampaignContact: (v: string) => void;
  createCampaign: () => Promise<void>;
  handleCallNow: (campaignId: string) => Promise<void>;
  handleSendEmail: (campaignId: string) => Promise<void>;
  handleGenerateOutreach: (campaignId: string) => Promise<void>;
  actionLoading: Record<string, boolean>;

  // Campaign sections
  expandedCampaigns: Record<string, string | null>;
  toggleCampaignSection: (campaignId: string, section: string) => void;
  editingEmails: Record<string, string>;
  setEditingEmails: React.Dispatch<React.SetStateAction<Record<string, string>>>;

  // Research
  researchResults: Record<string, ResearchResult>;
  researchLoading: Record<string, boolean>;
  handleResearch: (matchId: string) => Promise<void>;
  setResearchResults: React.Dispatch<
    React.SetStateAction<Record<string, ResearchResult>>
  >;

  // Autopilot
  autopilotStatus: AutopilotStatus | null;
  autopilotRunning: boolean;
  handleRunAutopilot: () => Promise<void>;

  // Helpers
  getEmailStatus: (campaign: Campaign) => "sent" | "draft" | "none";
  getCallStatus: (campaign: Campaign) => "completed" | "pending" | "none" | "failed";
  getLinkedinStatus: (campaign: Campaign) => "sent" | "draft" | "none";
  copyToClipboard: (text: string) => void;

  // Tab switching utility for cross-tab nav
  setTab: (tab: Tab) => void;

  // Toast
  showToast: (message: string, type: "success" | "error" | "info") => void;
}

export interface ContactFormState {
  company: string;
  name: string;
  title: string;
  phone: string;
  email: string;
}

const EMPTY_CONTACT_FORM: ContactFormState = {
  company: "",
  name: "",
  title: "",
  phone: "",
  email: "",
};

export function useOutreachData(
  setTabExternal: (tab: Tab) => void,
  showToast: (message: string, type: "success" | "error" | "info") => void,
): OutreachData {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  // Networking
  const [showAddForm, setShowAddForm] = useState(false);
  const [contactForm, setContactForm] =
    useState<ContactFormState>(EMPTY_CONTACT_FORM);
  const [savingContact, setSavingContact] = useState(false);

  // Research
  const [researchResults, setResearchResults] = useState<
    Record<string, ResearchResult>
  >({});
  const [researchLoading, setResearchLoading] = useState<
    Record<string, boolean>
  >({});

  // Autopilot
  const [autopilotStatus, setAutopilotStatus] =
    useState<AutopilotStatus | null>(null);
  const [autopilotRunning, setAutopilotRunning] = useState(false);

  // Campaigns
  const [expandedCampaigns, setExpandedCampaigns] = useState<
    Record<string, string | null>
  >({});
  const [editingEmails, setEditingEmails] = useState<Record<string, string>>(
    {},
  );
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>(
    {},
  );
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [newCampaignMatch, setNewCampaignMatch] = useState("");
  const [newCampaignContact, setNewCampaignContact] = useState("");

  // ── Data loading ───────────────────────────────────────────────────
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
          (m: Match) => m.composite_score > 0,
        ),
      );
    } catch {
      showToast("Failed to load data", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const loadAutopilotStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/autopilot/status`);
      if (res.ok) {
        const data = await res.json();
        setAutopilotStatus(data);
      }
    } catch {
      // Autopilot may not be configured
    }
  }, []);

  useEffect(() => {
    loadData();
    loadAutopilotStatus();
  }, [loadData, loadAutopilotStatus]);

  // ── Contacts ───────────────────────────────────────────────────────
  const contactsByCompany = useMemo(() => {
    const groups: Record<string, Contact[]> = {};
    for (const c of contacts) {
      const key = c.company || "Unknown";
      if (!groups[key]) groups[key] = [];
      groups[key] = [...groups[key], c];
    }
    return groups;
  }, [contacts]);

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
        setContactForm(EMPTY_CONTACT_FORM);
        setShowAddForm(false);
        showToast("Contact added", "success");
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed" }));
        showToast(err.detail || "Failed to add contact", "error");
      }
    } catch {
      showToast("Network error", "error");
    } finally {
      setSavingContact(false);
    }
  }

  async function removeContact(id: string) {
    try {
      await fetch(`${API}/contacts/${id}`, { method: "DELETE" });
      setContacts((prev) => prev.filter((c) => c.id !== id));
      showToast("Contact removed", "info");
    } catch {
      showToast("Failed to remove contact", "error");
    }
  }

  // ── Research ───────────────────────────────────────────────────────
  async function handleResearch(matchId: string) {
    setResearchLoading((prev) => ({ ...prev, [matchId]: true }));
    try {
      const res = await fetch(`${API}/research/${matchId}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setResearchResults((prev) => ({ ...prev, [matchId]: data }));
        showToast("Research complete", "success");
      } else {
        showToast("Research failed", "error");
      }
    } catch {
      showToast("Research request failed", "error");
    } finally {
      setResearchLoading((prev) => ({ ...prev, [matchId]: false }));
    }
  }

  // ── Autopilot ──────────────────────────────────────────────────────
  async function handleRunAutopilot() {
    setAutopilotRunning(true);
    try {
      const res = await fetch(`${API}/autopilot/run`, { method: "POST" });
      if (res.ok) {
        showToast("Autopilot cycle complete", "success");
        loadAutopilotStatus();
        loadData();
      } else {
        showToast("Autopilot run failed", "error");
      }
    } catch {
      showToast("Autopilot request failed", "error");
    } finally {
      setAutopilotRunning(false);
    }
  }

  // ── Campaigns ──────────────────────────────────────────────────────
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
        showToast("Campaign created", "success");
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed" }));
        showToast(err.detail || "Failed to create campaign", "error");
      }
    } catch {
      showToast("Network error", "error");
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
          prev.map((c) => (c.id === campaignId ? updated : c)),
        );
        showToast("Call initiated", "success");
      } else {
        const err = await res.json().catch(() => ({ detail: "Call failed" }));
        showToast(err.detail || "Call failed", "error");
      }
    } catch {
      showToast("Network error", "error");
    } finally {
      setActionLoading((prev) => ({
        ...prev,
        [`call_${campaignId}`]: false,
      }));
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
          prev.map((c) => (c.id === campaignId ? updated : c)),
        );
        showToast("Email sent", "success");
      } else {
        showToast("Failed to send email", "error");
      }
    } catch {
      showToast("Network error", "error");
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
        { method: "POST" },
      );
      if (res.ok) {
        const updated = await res.json();
        setCampaigns((prev) =>
          prev.map((c) => (c.id === campaignId ? updated : c)),
        );
        showToast("Outreach package generated", "success");
      } else {
        showToast("Failed to generate outreach", "error");
      }
    } catch {
      showToast("Network error", "error");
    } finally {
      setActionLoading((prev) => ({
        ...prev,
        [`outreach_${campaignId}`]: false,
      }));
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────
  function toggleCampaignSection(campaignId: string, section: string) {
    setExpandedCampaigns((prev) => ({
      ...prev,
      [campaignId]: prev[campaignId] === section ? null : section,
    }));
  }

  function getEmailStatus(
    campaign: Campaign,
  ): "sent" | "draft" | "none" {
    if (campaign.status === "completed" && campaign.email_draft)
      return "sent";
    if (campaign.email_draft) return "draft";
    return "none";
  }

  function getCallStatus(
    campaign: Campaign,
  ): "completed" | "pending" | "none" | "failed" {
    if (campaign.status === "completed") return "completed";
    if (campaign.status === "failed") return "failed";
    if (campaign.attempt_count > 0) return "pending";
    return "none";
  }

  function getLinkedinStatus(
    campaign: Campaign,
  ): "sent" | "draft" | "none" {
    if (campaign.linkedin_msg) return "draft";
    return "none";
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    showToast("Copied to clipboard", "info");
  }

  return {
    contacts,
    campaigns,
    matches,
    loading,
    contactsByCompany,
    showAddForm,
    setShowAddForm,
    contactForm,
    setContactForm,
    savingContact,
    addContact,
    removeContact,
    showCreateCampaign,
    setShowCreateCampaign,
    newCampaignMatch,
    setNewCampaignMatch,
    newCampaignContact,
    setNewCampaignContact,
    createCampaign,
    handleCallNow,
    handleSendEmail,
    handleGenerateOutreach,
    actionLoading,
    expandedCampaigns,
    toggleCampaignSection,
    editingEmails,
    setEditingEmails,
    researchResults,
    researchLoading,
    handleResearch,
    setResearchResults,
    autopilotStatus,
    autopilotRunning,
    handleRunAutopilot,
    getEmailStatus,
    getCallStatus,
    getLinkedinStatus,
    copyToClipboard,
    setTab: setTabExternal,
    showToast,
  };
}
