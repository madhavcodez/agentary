import Nav from "@/components/Nav";

export default function SettingsPage() {
  return (
    <>
      <Nav />
      <main className="ml-64 p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">Settings coming soon</p>
          <p className="text-sm text-gray-600 mt-2">Configure API keys, integrations, and platform preferences</p>
        </div>
      </main>
    </>
  );
}
