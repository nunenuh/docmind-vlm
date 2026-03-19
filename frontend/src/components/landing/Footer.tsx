import { FileText, Github } from "lucide-react";

export function Footer() {
  return (
    <footer className="py-12 bg-gray-950 border-t border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2 text-gray-400">
            <FileText className="w-5 h-5" />
            <span className="font-medium text-white">DocMind-VLM</span>
          </div>

          <div className="flex items-center gap-6 text-sm text-gray-500">
            <a
              href="https://github.com/nunenuh/docmind-vlm"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 hover:text-gray-300 transition-colors"
            >
              <Github className="w-4 h-4" />
              GitHub
            </a>
            <a
              href="https://nunenuh.me"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-300 transition-colors"
            >
              nunenuh.me
            </a>
            <span>MIT License</span>
          </div>

          <p className="text-sm text-gray-600">
            &copy; 2026 DocMind-VLM
          </p>
        </div>
      </div>
    </footer>
  );
}
