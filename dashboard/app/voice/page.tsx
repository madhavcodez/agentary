import Nav from "@/components/Nav";

export default function VoicePage() {
  return (
    <>
      <Nav />
      <main className="ml-64 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white">Voice</h1>
          <button className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors">
            New Extraction
          </button>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">No voice extractions yet</p>
          <p className="text-sm text-gray-600 mt-2">Set up voice-based data extraction campaigns for your projects</p>
        </div>
      </main>
    </>
  );
}
