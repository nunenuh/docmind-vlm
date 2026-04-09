import { FileUp, Eye, GitCompare, MessageSquare, Library } from "lucide-react";
import type { ReactNode } from "react";

interface FeatureItem {
  icon: ReactNode;
  title: string;
  description: string;
  detail: string;
}

const features: FeatureItem[] = [
  {
    icon: <FileUp className="w-6 h-6" />,
    title: "Extract",
    description: "Upload any doc. Get structured data instantly.",
    detail:
      "PDFs, images, scanned documents — our VLM extracts key-value pairs, tables, and entities with per-field confidence scores and precise bounding boxes.",
  },
  {
    icon: <Eye className="w-6 h-6" />,
    title: "Understand",
    description: "See where the AI is confident — and where it's not.",
    detail:
      "Color-coded confidence overlays show exactly which fields the model is sure about. Low-confidence fields get human-readable explanations.",
  },
  {
    icon: <GitCompare className="w-6 h-6" />,
    title: "Compare",
    description: "Raw VLM vs enhanced. See the difference.",
    detail:
      "Side-by-side comparison of raw VLM output and post-processed results. See which fields were corrected, added, or left unchanged.",
  },
  {
    icon: <MessageSquare className="w-6 h-6" />,
    title: "Chat",
    description: "Ask questions. Get answers with source citations.",
    detail:
      "Natural language Q&A grounded in the document data. Every answer includes page citations and bounding box references you can verify.",
  },
  {
    icon: <Library className="w-6 h-6" />,
    title: "Knowledge Base",
    description: "Build a searchable knowledge base from all your documents.",
    detail:
      "Upload multiple documents into a project, index them with pgvector embeddings, and chat across your entire collection with a configurable AI persona using RAG.",
  },
];

export function Features() {
  return (
    <section id="features" className="py-24 bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Everything you need to understand documents
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            From extraction to conversation, DocMind-VLM handles the full pipeline.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group bg-gray-900/50 border border-gray-800 rounded-xl p-8 hover:border-blue-500/30 transition-all duration-200 hover:bg-gray-900/70"
            >
              <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center text-blue-400 mb-5 group-hover:bg-blue-500/20 transition-colors">
                {feature.icon}
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                {feature.title}
              </h3>
              <p className="text-blue-300 font-medium mb-3">
                {feature.description}
              </p>
              <p className="text-gray-400 text-sm leading-relaxed">
                {feature.detail}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
