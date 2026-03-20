import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-blue-950/30 via-gray-950 to-gray-950" />
      <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 mb-8">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="text-sm text-blue-300">Powered by Vision Language Models</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
          Extract, understand, and{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
            chat with your documents.
          </span>
        </h1>

        <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10">
          Upload PDFs or images for AI-powered data extraction with confidence scores.
          Build a Knowledge Base across multiple documents and chat with a configurable AI persona.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/login"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-8 py-3 rounded-lg transition-colors text-lg"
          >
            Get Started
            <ArrowRight className="w-5 h-5" />
          </Link>
          <a
            href="https://github.com/nunenuh/docmind-vlm"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-medium px-8 py-3 rounded-lg transition-colors text-lg"
          >
            View on GitHub
          </a>
        </div>

        <div className="mt-16 relative">
          <div className="aspect-video max-w-4xl mx-auto bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-2xl shadow-blue-500/5">
            <div className="w-full h-full flex items-center justify-center text-gray-600">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-lg bg-gray-800 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-blue-500/50" />
                </div>
                <p className="text-sm">Interactive demo preview</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
