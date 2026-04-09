# Issue #27: Dashboard Page — Document List, Upload, and Management

## Summary

Implement the Dashboard page with a document card grid, drag-and-drop upload area, empty state, loading skeletons, and document management (delete). Integrates with the existing `useDocuments`, `useCreateDocument`, and `useDeleteDocument` hooks which call the backend API. The upload flow: user drops a file, it uploads to Supabase Storage, then creates a document record via the API, and the document list refreshes. Includes pagination for large collections.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #26 (AuthGuard wraps this page)
- **Branch**: `feat/27-dashboard`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — UploadArea full implementation, DocumentCard spec, component conventions
- `specs/frontend/state.md` — useDocuments hook, React Query patterns, loading/error patterns
- `specs/frontend/api-client.md` — createDocument, fetchDocuments, deleteDocument, uploadDocument (Supabase storage)
- `docs/blueprint/02-product/user-interface-specification.md` — Section 2.2 Dashboard
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 2.1 through AC 2.6

## Current State (Scaffold)

**File: `frontend/src/pages/Dashboard.tsx`**
```typescript
export function Dashboard() {
  return <div className="min-h-screen p-8"><h1 className="text-2xl font-bold">Dashboard</h1></div>;
}
```

**File: `frontend/src/components/workspace/UploadArea.tsx`**
```typescript
export function UploadArea() {
  return <div>UploadArea</div>;
}
```

**File: `frontend/src/hooks/useDocuments.ts`** (already implemented):
```typescript
export function useDocuments(page = 1, limit = 20) {
  return useQuery({ queryKey: ["documents", page, limit], queryFn: () => fetchDocuments(page, limit) });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DocumentCreate) => createDocument(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["documents"] }); },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["documents"] }); },
  });
}
```

**Missing files:**
- `frontend/src/components/dashboard/DocumentCard.tsx`
- `frontend/src/components/dashboard/DocumentGrid.tsx`
- `frontend/src/components/dashboard/EmptyState.tsx`
- `frontend/src/components/dashboard/DashboardSkeleton.tsx`

## Requirements

### Functional

1. **Document Grid**: Display documents as a responsive card grid. Each card shows: filename, upload date, file type badge, processing status badge (uploaded/processing/ready/error), file size.
2. **UploadArea**: Drag-and-drop zone at the top of the page. Accepts PDF, PNG, JPG, JPEG, TIFF, WebP. Max 20MB. Shows progress bar during upload. Validates file type and size client-side with clear error messages.
3. **Upload Flow**: File dropped -> upload to Supabase Storage -> create document record via API -> invalidate document list query -> new document appears in grid.
4. **Empty State**: When no documents exist, show encouraging message with upload prompt.
5. **Document Actions**: Each card has a dropdown menu with "Open" (navigate to workspace) and "Delete" (with confirmation dialog).
6. **Pagination**: Show page controls when total documents exceed the page limit (20).
7. **Loading State**: Show skeleton cards while documents are loading.
8. **Error State**: Show error message if document fetch fails.

### Non-Functional

- File validation happens client-side before upload attempt
- Upload progress displayed in real-time
- Optimistic UI: card appears immediately after upload with "uploading" status
- Card grid uses CSS grid with responsive columns: 1 on mobile, 2 on tablet, 3-4 on desktop
- All card interactions are keyboard-accessible

## Implementation Plan

### Component Tree

```
Dashboard.tsx
├── DashboardHeader           (inline — logo, user email, logout)
├── UploadArea.tsx             (drag-drop + file picker)
├── DocumentGrid.tsx           (responsive grid wrapper)
│   ├── DocumentCard.tsx       (repeated for each document)
│   │   └── DropdownMenu       (Open, Delete actions)
│   └── EmptyState.tsx         (shown when no documents)
├── DashboardSkeleton.tsx      (loading state)
└── Pagination                 (page controls)
```

### Key Components

**`frontend/src/components/dashboard/DocumentCard.tsx`**:
```typescript
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreVertical, Trash2, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import type { DocumentResponse } from "@/types/api";

interface DocumentCardProps {
  document: DocumentResponse;
  onDelete: (id: string) => void;
}

const STATUS_STYLES: Record<string, string> = {
  uploaded: "bg-blue-100 text-blue-800",
  processing: "bg-yellow-100 text-yellow-800",
  ready: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const navigate = useNavigate();

  return (
    <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => navigate(`/workspace/${document.id}`)}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium truncate">{document.filename}</h3>
          <p className="text-xs text-muted-foreground mt-1">
            {new Date(document.created_at).toLocaleDateString()}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => navigate(`/workspace/${document.id}`)}>
              <ExternalLink className="h-4 w-4 mr-2" /> Open
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive" onClick={() => onDelete(document.id)}>
              <Trash2 className="h-4 w-4 mr-2" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="flex items-center gap-2 mt-3">
        <Badge variant="secondary" className="text-xs">{document.file_type.toUpperCase()}</Badge>
        <Badge className={`text-xs ${STATUS_STYLES[document.status]}`}>{document.status}</Badge>
        <span className="text-xs text-muted-foreground ml-auto">
          {(document.file_size / 1024 / 1024).toFixed(1)} MB
        </span>
      </div>
    </Card>
  );
}
```

**`frontend/src/components/workspace/UploadArea.tsx`** (implement per spec):
```typescript
// Full implementation from specs/frontend/components.md — UploadArea section
// Key features:
// - Drag-and-drop with isDragOver visual state
// - File validation: ACCEPTED_TYPES set, MAX_FILE_SIZE = 20MB
// - Progress bar during upload (isUploading + progress props)
// - Error display for invalid files
// - Clear selection button

interface UploadAreaProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
  progress: number;
}
```

**Upload Flow in Dashboard.tsx**:
```typescript
const handleUpload = async (file: File) => {
  setIsUploading(true);
  try {
    const documentId = crypto.randomUUID();
    const userId = user?.id;
    if (!userId) throw new Error("Not authenticated");

    // 1. Upload to Supabase Storage
    const { error: uploadError } = await uploadDocument(file, userId, documentId);
    if (uploadError) throw uploadError;

    // 2. Create document record via API
    await createDocumentMutation.mutateAsync({
      filename: file.name,
      file_type: file.name.split(".").pop() ?? "unknown",
      file_size: file.size,
      storage_path: `${userId}/${documentId}/${file.name}`,
    });
  } catch (err) {
    setUploadError(err instanceof Error ? err.message : "Upload failed");
  } finally {
    setIsUploading(false);
  }
};
```

### shadcn/ui Components Needed

```bash
cd frontend
npx shadcn@latest add card badge button dropdown-menu dialog progress
```

## Acceptance Criteria

- [ ] Drag-and-drop file upload works and processing begins — AC 2.1
- [ ] Click upload area opens file picker as fallback — AC 2.2
- [ ] Upload progress bar visible and updates in real time — AC 2.3
- [ ] Files > 20MB rejected with clear error message — AC 2.4
- [ ] Unsupported formats rejected with clear error message — AC 2.5
- [ ] Documents stored in Supabase Storage with unique path — AC 2.6
- [ ] Document grid shows all user documents with status badges
- [ ] Empty state shown when no documents exist
- [ ] Loading skeletons shown while fetching
- [ ] Delete with confirmation dialog works
- [ ] Pagination controls shown for > 20 documents
- [ ] Clicking a card navigates to `/workspace/:id`

## Files Changed

- `frontend/src/pages/Dashboard.tsx` — full implementation
- `frontend/src/components/workspace/UploadArea.tsx` — implement from stub (per spec)
- `frontend/src/components/dashboard/DocumentCard.tsx` — new file
- `frontend/src/components/dashboard/DocumentGrid.tsx` — new file
- `frontend/src/components/dashboard/EmptyState.tsx` — new file
- `frontend/src/components/dashboard/DashboardSkeleton.tsx` — new file

## Verification

```bash
cd frontend
npm run typecheck
npm run lint
npm run dev
# Manual testing:
# 1. Visit /dashboard with auth → see empty state
# 2. Drag a PDF → upload progress → document card appears
# 3. Drag a .exe file → error message shown
# 4. Drag a 25MB file → size error shown
# 5. Click document card → navigate to /workspace/:id
# 6. Click delete → confirmation dialog → document removed
# 7. Upload 25+ documents → pagination controls appear
```
