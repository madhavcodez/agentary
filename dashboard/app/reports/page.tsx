import Nav from "@/components/Nav";

export default function ReportsPage() {
  return (
    <>
      <Nav />
      <main className="ml-64 p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Reports</h1>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">No reports generated yet</p>
          <p className="text-sm text-gray-600 mt-2">Reports will appear here after missions produce findings</p>
        </div>
      </main>
    </>
  );
}
