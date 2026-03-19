import { useRef, useState, useCallback } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { OverlayRegion } from "@/types/api";

interface DocumentViewerProps {
  imageUrl?: string;
  overlayRegions?: OverlayRegion[];
}

export function DocumentViewer({ imageUrl, overlayRegions = [] }: DocumentViewerProps) {
  const { zoomLevel, setZoomLevel, selectedFieldId, overlayMode } = useWorkspaceStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragStart = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y,
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => setIsDragging(false), []);

  const resetView = useCallback(() => {
    setZoomLevel(1.0);
    setOffset({ x: 0, y: 0 });
  }, [setZoomLevel]);

  return (
    <div className="flex flex-col h-full bg-gray-950">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900/50">
        <span className="text-sm text-gray-400">Document Viewer</span>
        <div className="flex items-center gap-1">
          <button onClick={() => setZoomLevel(zoomLevel - 0.25)} className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors" aria-label="Zoom out">
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500 w-12 text-center">{Math.round(zoomLevel * 100)}%</span>
          <button onClick={() => setZoomLevel(zoomLevel + 0.25)} className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors" aria-label="Zoom in">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={resetView} className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors ml-1" aria-label="Reset view">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing" onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        <div className="relative inline-block origin-top-left" style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoomLevel})` }}>
          {imageUrl ? (
            <img src={imageUrl} alt="Document page" className="max-w-none select-none" draggable={false} />
          ) : (
            <div className="w-[595px] h-[842px] bg-gray-900 border border-gray-800 flex items-center justify-center">
              <p className="text-gray-600 text-sm">No document loaded</p>
            </div>
          )}
          {overlayMode !== "none" && overlayRegions.map((region, i) => (
            <div
              key={i}
              className={`absolute border-2 transition-colors ${selectedFieldId === String(i) ? "border-blue-400 bg-blue-400/20" : "border-current bg-current/10"}`}
              style={{ left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.width * 100}%`, height: `${region.height * 100}%`, color: region.color }}
              title={region.tooltip ?? undefined}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
