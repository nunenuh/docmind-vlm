# Project Workspace Redesign — Tab-Based Layout

## Problem

Current project workspace crams documents + conversations into a narrow sidebar. Unusable with many files. No room for upload progress, error states, indexing status.

## Solution

Replace sidebar layout with **full-width tabs**:

```
┌──────────┬──────────────────────────────────────────────────────┐
│ App      │  Project Name  ⚙ Settings                            │
│ Sidebar  │  [Documents]  [Chat]                                 │
│          ├──────────────────────────────────────────────────────┤
│          │                                                      │
│          │  Tab content (full width)                             │
│          │                                                      │
│          │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

## Documents Tab

Full-width document management:

```
┌──────────────────────────────────────────────────────┐
│  Documents (6)                    [+ Upload Files]    │
├──────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────┐  │
│  │ 📄 report.pdf           110 pages   2.7 MB     │  │
│  │    ████████████████████  Indexed ✓  135 chunks  │  │
│  │                                    [⟳] [🗑]    │  │
│  ├────────────────────────────────────────────────┤  │
│  │ 📄 ktp.jpg                1 page   423 KB      │  │
│  │    ████████████████████  Indexed ✓  3 chunks    │  │
│  │                                    [⟳] [🗑]    │  │
│  ├────────────────────────────────────────────────┤  │
│  │ 📄 contract.pdf          15 pages  1.1 MB      │  │
│  │    ████████░░░░░░░░░░░░  Indexing   42/87       │  │
│  ├────────────────────────────────────────────────┤  │
│  │ 📄 broken.pdf             ERROR                 │  │
│  │    Connection timed out                         │  │
│  │    [Retry Index]                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │  Drop files here or click to upload            │  │
│  │  PDF, PNG, JPG, TIFF, WebP — up to 20MB        │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
└──────────────────────────────────────────────────────┘
```

Each document card shows:
- Filename, page count, file size
- Index status: uploaded / indexing (with progress) / indexed (chunk count) / error
- Reindex button, delete button
- Error message + retry for failed indexing

## Chat Tab

Full-width chat with conversation list:

```
┌────────────────────┬─────────────────────────────────┐
│  Conversations     │  Chat                            │
│                    │                                  │
│  🗨 hi?            │  [Thinking...]                   │
│  🗨 prosedur...    │                                  │
│  🗨 dokumen apa... │  Based on the documents...       │
│                    │                                  │
│                    │  Source 1 p.3  Source 2 p.1       │
│                    │                                  │
│  [+ New Chat]      │  [Ask about your documents...]   │
└────────────────────┴─────────────────────────────────┘
```

Conversation sidebar is ~250px, chat takes remaining width.

## Implementation

Replace `ProjectWorkspace.tsx` and `ProjectSidebar.tsx` with:

1. `ProjectWorkspace.tsx` — tab container (Documents | Chat) + header
2. `ProjectDocumentsTab.tsx` — full document list with upload + status
3. `ProjectChatTab.tsx` — conversation sidebar + chat panel (reuse ProjectChatPanel)
