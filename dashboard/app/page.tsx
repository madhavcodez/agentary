import Nav from "@/components/Nav";

export default function DashboardPage() {
  return (
    <>
      <Nav />
      <main className="ml-64 p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { label: "Active Projects", value: "0", color: "emerald" },
            { label: "Running Missions", value: "0", color: "blue" },
            { label: "Total Findings", value: "0", color: "amber" },
            { label: "Reports Generated", value: "0", color: "purple" },
          ].map((stat) => (
            <div key={stat.label} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <p className="text-sm text-gray-400">{stat.label}</p>
              <p className={`text-3xl font-bold text-${stat.color}-400 mt-2`}>{stat.value}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
          <p className="text-gray-400">Live agent feed will appear here</p>
          <p className="text-sm text-gray-600 mt-2">Create a project and run a mission to see agents in action</p>
        </div>
      </main>
    </>
  );
}
