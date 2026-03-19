import { Upload, Cpu, CheckCircle, MessageCircle, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

interface Step {
  icon: ReactNode;
  title: string;
  description: string;
}

const steps: Step[] = [
  {
    icon: <Upload className="w-7 h-7" />,
    title: "Upload",
    description: "Drop any PDF or image document",
  },
  {
    icon: <Cpu className="w-7 h-7" />,
    title: "Extract",
    description: "VLM extracts structured fields",
  },
  {
    icon: <CheckCircle className="w-7 h-7" />,
    title: "Verify",
    description: "Review confidence scores and overlays",
  },
  {
    icon: <MessageCircle className="w-7 h-7" />,
    title: "Chat",
    description: "Ask questions with cited answers",
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 bg-gray-900/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            How it works
          </h2>
          <p className="text-lg text-gray-400">
            Four steps from document to insights
          </p>
        </div>

        <div className="flex flex-col md:flex-row items-start md:items-center justify-center gap-4 md:gap-0">
          {steps.map((step, i) => (
            <div key={step.title} className="flex items-center">
              <div className="flex flex-col items-center text-center w-48">
                <div className="w-16 h-16 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center text-blue-400 mb-4">
                  {step.icon}
                </div>
                <h3 className="text-white font-semibold mb-1">{step.title}</h3>
                <p className="text-gray-400 text-sm">{step.description}</p>
              </div>
              {i < steps.length - 1 && (
                <ArrowRight className="hidden md:block w-5 h-5 text-gray-600 mx-4 flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
