const techItems = [
  { name: "Qwen3-VL", category: "VLM" },
  { name: "LangGraph", category: "Pipeline" },
  { name: "FastAPI", category: "Backend" },
  { name: "React", category: "Frontend" },
  { name: "Supabase", category: "Database" },
  { name: "OpenCV", category: "CV" },
  { name: "TypeScript", category: "Language" },
  { name: "Tailwind", category: "Styling" },
];

export function TechStack() {
  return (
    <section className="py-24 bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Built with modern tools
          </h2>
          <p className="text-lg text-gray-400">
            Production-grade stack from extraction to UI
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4">
          {techItems.map((item) => (
            <div
              key={item.name}
              className="bg-gray-900/50 border border-gray-800 rounded-lg px-5 py-3 flex items-center gap-3 hover:border-gray-700 transition-colors"
            >
              <span className="text-white font-medium">{item.name}</span>
              <span className="text-xs text-gray-500 bg-gray-800 rounded px-2 py-0.5">
                {item.category}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
