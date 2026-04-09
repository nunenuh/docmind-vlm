import { FileText, Github } from "lucide-react";
import { Link } from "react-router-dom";

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-white font-bold text-lg">
          <FileText className="w-6 h-6 text-blue-400" />
          DocMind-VLM
        </Link>
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="text-sm text-gray-400 hover:text-white transition-colors hidden sm:block"
          >
            Documents
          </Link>
          <Link
            to="/projects"
            className="text-sm text-gray-400 hover:text-white transition-colors hidden sm:block"
          >
            Projects
          </Link>
          <a
            href="https://github.com/nunenuh/docmind-vlm"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="GitHub repository"
          >
            <Github className="w-5 h-5" />
          </a>
          <Link
            to="/login"
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Try it Free
          </Link>
        </div>
      </div>
    </nav>
  );
}
