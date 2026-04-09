import { Play } from "lucide-react";

export function Demo() {
  return (
    <section className="py-24 bg-gray-900/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            See it in action
          </h2>
          <p className="text-lg text-gray-400">
            Watch how DocMind-VLM processes a real document
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <div className="aspect-video bg-gray-900 rounded-xl border border-gray-800 overflow-hidden relative group cursor-pointer hover:border-gray-700 transition-colors">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-20 h-20 bg-blue-600/80 group-hover:bg-blue-500 rounded-full flex items-center justify-center transition-colors shadow-lg shadow-blue-500/20">
                <Play className="w-8 h-8 text-white ml-1" />
              </div>
            </div>
            <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-sm text-gray-500">
              <span>Demo video coming soon</span>
              <span>~2 min</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
