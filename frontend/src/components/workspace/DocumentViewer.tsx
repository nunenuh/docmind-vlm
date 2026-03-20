import { useRef, useState, useCallback } from "react";
import { ZoomIn, ZoomOut, RotateCcw, FileText, Loader2 } from "lucide-react";
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
  const [isImageLoading, setIsImageLoading] = useState(true);
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
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 h-10 border-b border-gray-800 bg-gray-900/30 flex-shrink-0">
        <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Viewer</span>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setZoomLevel(Math.max(0.25, zoomLevel - 0.25))}
            className="p-1.5 rounded-md hover:bg-gray-800 text-gray-400 hover:text-white transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500 w-12 text-center tabular-nums">{Math.round(zoomLevel * 100)}%</span>
          <button
            onClick={() => setZoomLevel(Math.min(4, zoomLevel + 0.25))}
            className="p-1.5 rounded-md hover:bg-gray-800 text-gray-400 hover:text-white transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <div className="w-px h-4 bg-gray-800 mx-1" />
          <button
            onClick={resetView}
            className="p-1.5 rounded-md hover:bg-gray-800 text-gray-400 hover:text-white transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Reset view"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {imageUrl ? (
          <>
            {/* Loading state for image */}
            {isImageLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                <p className="text-sm text-gray-500 mt-3">Loading document...</p>
              </div>
            )}
            <div
              className="relative w-full h-full flex items-start justify-center pt-4"
              style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
            >
              <div className="relative" style={{ transform: `scale(${zoomLevel})`, transformOrigin: "top center" }}>
                <img
                  src={imageUrl}
                  alt="Document page"
                  className={`max-w-none select-none transition-opacity duration-300 ${isImageLoading ? "opacity-0" : "opacity-100"}`}
                  draggable={false}
                  onLoad={() => setIsImageLoading(false)}
                />
                {overlayMode !== "none" && overlayRegions.map((region, i) => (
                  <div
                    key={i}
                    className={`absolute border-2 transition-all duration-200 ${selectedFieldId === String(i) ? "border-blue-400 bg-blue-400/20" : "border-current bg-current/10"}`}
                    style={{ left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.width * 100}%`, height: `${region.height * 100}%`, color: region.color }}
                    title={region.tooltip ?? undefined}
                  />
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="w-20 h-20 rounded-2xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-5">
              <FileText className="w-10 h-10 text-gray-700" />
            </div>
            <p className="text-sm font-medium text-gray-400 mb-1">No document loaded</p>
            <p className="text-xs text-gray-600">Process the document to view it here</p>
          </div>
        )}
      </div>
    </div>
  );
}
