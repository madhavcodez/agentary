import Nav from "@/components/Nav";

export default function ProjectsPage() {
  return (
    <>
      <Nav />
      <main className="ml-64 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <button className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors">
            New Project
          </button>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">No projects yet</p>
          <p className="text-sm text-gray-600 mt-2">Create your first research project to get started</p>
        </div>
      </main>
    </>
  );
}
