"use client";

import { useState, useCallback } from "react";
import Spinner from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import OutreachTabs from "@/components/outreach/OutreachTabs";
import NetworkingTab from "@/components/outreach/NetworkingTab";
import CampaignTab from "@/components/outreach/CampaignTab";
import ConversationsTab from "@/components/outreach/ConversationsTab";
import IdeasTab from "@/components/outreach/IdeasTab";
import { useOutreachData, type Tab } from "@/lib/hooks/useOutreachData";

export default function OutreachPage() {
  const [tab, setTab] = useState<Tab>("networking");
  const { toast } = useToast();

  const showToast = useCallback(
    (message: string, type: "success" | "error" | "info") => {
      toast(message, type);
    },
    [toast],
  );

  const data = useOutreachData(setTab, showToast);

  if (data.loading) {
    return (
      <div className="max-w-6xl">
        <div className="text-center py-16">
          <Spinner size="lg" className="mx-auto" />
          <p className="text-sm text-gray-500 mt-4">
            Loading outreach data...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Outreach</h1>
        <p className="text-sm text-gray-400 mt-1">
          Multi-channel outreach: networking, cold email, calls, and LinkedIn
        </p>
      </div>

      <OutreachTabs activeTab={tab} onTabChange={setTab} />

      {tab === "networking" && <NetworkingTab data={data} />}
      {tab === "outreach" && <CampaignTab data={data} />}
      {tab === "conversations" && <ConversationsTab data={data} />}
      {tab === "ideas" && <IdeasTab data={data} />}
    </div>
  );
}
