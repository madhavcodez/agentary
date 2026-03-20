"use client";

import { cn } from "@/lib/cn";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import CampaignRow from "./CampaignRow";
import type { OutreachData } from "@/lib/hooks/useOutreachData";

interface CampaignTabProps {
  data: OutreachData;
}

export default function CampaignTab({ data }: CampaignTabProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-200">
          Campaigns ({data.campaigns.length})
        </h2>
        <Button
          size="sm"
          variant={data.showCreateCampaign ? "secondary" : "primary"}
          onClick={() => data.setShowCreateCampaign(!data.showCreateCampaign)}
          className={cn(
            !data.showCreateCampaign && "bg-emerald-600 hover:bg-emerald-500",
          )}
        >
          {data.showCreateCampaign ? "Cancel" : "+ New Campaign"}
        </Button>
      </div>

      {data.showCreateCampaign && (
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
                value={data.newCampaignMatch}
                onChange={(e) => data.setNewCampaignMatch(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
              >
                <option value="">Select a match...</option>
                {data.matches.slice(0, 20).map((m) => (
                  <option key={m.id} value={m.id}>
                    {Math.round(m.composite_score)} - {m.opportunity?.title}{" "}
                    at {m.opportunity?.company}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Contact
              </label>
              <select
                value={data.newCampaignContact}
                onChange={(e) => data.setNewCampaignContact(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
              >
                <option value="">Select a contact...</option>
                {data.contacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.company} - {c.company}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button
            loading={data.actionLoading.createCampaign}
            disabled={!data.newCampaignMatch || !data.newCampaignContact}
            onClick={data.createCampaign}
            className="bg-emerald-600 hover:bg-emerald-500"
          >
            {data.actionLoading.createCampaign
              ? "Creating..."
              : "Create Campaign"}
          </Button>
        </div>
      )}

      {data.campaigns.length === 0 ? (
        <EmptyState
          icon={
            <svg
              className="w-10 h-10 text-gray-700"
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
          }
          title="No campaigns yet."
          description="Create one by selecting a match and a contact above."
        />
      ) : (
        <div className="space-y-3">
          {data.campaigns.map((camp) => (
            <CampaignRow
              key={camp.id}
              campaign={camp}
              expanded={data.expandedCampaigns[camp.id] ?? null}
              editingEmail={data.editingEmails[camp.id]}
              emailStatus={data.getEmailStatus(camp)}
              callStatus={data.getCallStatus(camp)}
              linkedinStatus={data.getLinkedinStatus(camp)}
              actionLoading={data.actionLoading}
              onToggleSection={data.toggleCampaignSection}
              onGenerateOutreach={data.handleGenerateOutreach}
              onSendEmail={data.handleSendEmail}
              onCallNow={data.handleCallNow}
              onEditEmail={(id, v) =>
                data.setEditingEmails((prev) => ({
                  ...prev,
                  [id]: v,
                }))
              }
              onCopyClipboard={data.copyToClipboard}
            />
          ))}
        </div>
      )}
    </div>
  );
}
