"use client";

import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import AddContactForm from "./AddContactForm";
import CompanyGroup from "./CompanyGroup";
import type { OutreachData } from "@/lib/hooks/useOutreachData";

interface NetworkingTabProps {
  data: OutreachData;
}

export default function NetworkingTab({ data }: NetworkingTabProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-200">
          Contacts ({data.contacts.length})
        </h2>
        <Button
          size="sm"
          variant={data.showAddForm ? "secondary" : "primary"}
          onClick={() => data.setShowAddForm(!data.showAddForm)}
        >
          {data.showAddForm ? "Cancel" : "+ Add Contact"}
        </Button>
      </div>

      {data.showAddForm && (
        <AddContactForm
          form={data.contactForm}
          onChange={data.setContactForm}
          onSubmit={data.addContact}
          saving={data.savingContact}
        />
      )}

      {Object.keys(data.contactsByCompany).length === 0 ? (
        <EmptyState
          icon={
            <svg className="w-10 h-10 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
          }
          title="No contacts yet."
          description="Add people you want to reach out to."
        />
      ) : (
        <div className="space-y-5">
          {Object.entries(data.contactsByCompany).map(
            ([company, companyContacts]) => {
              const companyMatch = data.matches.find(
                (m) =>
                  m.opportunity?.company?.toLowerCase() ===
                  company.toLowerCase(),
              );
              return (
                <CompanyGroup
                  key={company}
                  company={company}
                  contacts={companyContacts}
                  companyMatch={companyMatch}
                  researchLoading={
                    companyMatch
                      ? (data.researchLoading[companyMatch.id] ?? false)
                      : false
                  }
                  onResearch={data.handleResearch}
                  onRemoveContact={data.removeContact}
                />
              );
            },
          )}
        </div>
      )}
    </div>
  );
}
