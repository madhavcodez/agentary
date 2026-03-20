"use client";

import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import type { ContactFormState } from "@/lib/hooks/useOutreachData";

interface AddContactFormProps {
  form: ContactFormState;
  onChange: (form: ContactFormState) => void;
  onSubmit: (e: React.FormEvent) => Promise<void>;
  saving: boolean;
}

export default function AddContactForm({
  form,
  onChange,
  onSubmit,
  saving,
}: AddContactFormProps) {
  function update(field: keyof ContactFormState, value: string) {
    onChange({ ...form, [field]: value });
  }

  return (
    <Card className="p-5 mb-5">
      <h3 className="text-sm font-medium text-gray-300 mb-3">New Contact</h3>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-2 gap-3">
          <input
            value={form.company}
            onChange={(e) => update("company", e.target.value)}
            placeholder="Company *"
            required
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
          />
          <input
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="Name"
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
          />
          <input
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            placeholder="Title (e.g. Engineering Manager)"
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
          />
          <input
            value={form.phone}
            onChange={(e) => update("phone", e.target.value)}
            placeholder="Phone (+1...)"
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors"
          />
          <input
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            placeholder="Email"
            type="email"
            className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 focus:outline-none transition-colors col-span-2"
          />
        </div>
        <Button
          type="submit"
          loading={saving}
          disabled={!form.company.trim()}
          className="mt-3"
        >
          {saving ? "Saving..." : "Save Contact"}
        </Button>
      </form>
    </Card>
  );
}
