import { useState } from "react";
import { Copy, Check } from "lucide-react";

type Language = "curl" | "python" | "javascript";

const TABS: { id: Language; label: string }[] = [
  { id: "curl", label: "cURL" },
  { id: "python", label: "Python" },
  { id: "javascript", label: "JavaScript" },
];

const EXAMPLES: Record<Language, string> = {
  curl: `# List all documents
curl -H "Authorization: Bearer dm_live_xxxxxxxxxxxx" \\
  https://your-domain.com/api/v1/documents

# Upload a document
curl -X POST \\
  -H "Authorization: Bearer dm_live_xxxxxxxxxxxx" \\
  -F "file=@invoice.pdf" \\
  https://your-domain.com/api/v1/documents

# Get extraction results
curl -H "Authorization: Bearer dm_live_xxxxxxxxxxxx" \\
  https://your-domain.com/api/v1/extractions/{document_id}

# Search the RAG index
curl -X POST \\
  -H "Authorization: Bearer dm_live_xxxxxxxxxxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "invoice total amount"}' \\
  https://your-domain.com/api/v1/rag/search`,

  python: `import requests

API_KEY = "dm_live_xxxxxxxxxxxx"
BASE_URL = "https://your-domain.com/api/v1"
headers = {"Authorization": f"Bearer {API_KEY}"}

# List all documents
response = requests.get(f"{BASE_URL}/documents", headers=headers)
documents = response.json()

# Upload a document
with open("invoice.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/documents",
        headers=headers,
        files={"file": f},
    )
    document = response.json()

# Get extraction results
doc_id = document["id"]
response = requests.get(
    f"{BASE_URL}/extractions/{doc_id}",
    headers=headers,
)
extraction = response.json()

# Search the RAG index
response = requests.post(
    f"{BASE_URL}/rag/search",
    headers=headers,
    json={"query": "invoice total amount"},
)
results = response.json()`,

  javascript: `const API_KEY = "dm_live_xxxxxxxxxxxx";
const BASE_URL = "https://your-domain.com/api/v1";
const headers = { Authorization: \`Bearer \${API_KEY}\` };

// List all documents
const docsRes = await fetch(\`\${BASE_URL}/documents\`, { headers });
const documents = await docsRes.json();

// Upload a document
const formData = new FormData();
formData.append("file", fileInput.files[0]);
const uploadRes = await fetch(\`\${BASE_URL}/documents\`, {
  method: "POST",
  headers: { Authorization: \`Bearer \${API_KEY}\` },
  body: formData,
});
const document = await uploadRes.json();

// Get extraction results
const extRes = await fetch(
  \`\${BASE_URL}/extractions/\${document.id}\`,
  { headers },
);
const extraction = await extRes.json();

// Search the RAG index
const ragRes = await fetch(\`\${BASE_URL}/rag/search\`, {
  method: "POST",
  headers: { ...headers, "Content-Type": "application/json" },
  body: JSON.stringify({ query: "invoice total amount" }),
});
const results = await ragRes.json();`,
};

export function CodeExamples() {
  const [activeTab, setActiveTab] = useState<Language>("curl");
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(EXAMPLES[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1 bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setCopied(false);
              }}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === tab.id
                  ? "bg-indigo-600/10 text-indigo-400"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-500 hover:text-gray-300 border border-[#1e1e2e] hover:border-gray-700 rounded-lg transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>
      <pre className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-4 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre leading-relaxed">
        {EXAMPLES[activeTab]}
      </pre>
    </div>
  );
}
