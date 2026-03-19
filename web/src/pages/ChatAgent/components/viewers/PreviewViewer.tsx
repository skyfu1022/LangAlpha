import React, { useState, useCallback, useRef, useEffect } from 'react';
import { RefreshCw, ExternalLink, X, Loader2, Globe } from 'lucide-react';
import './PreviewViewer.css';

interface PreviewViewerProps {
  url: string;
  port: number;
  title?: string;
  onClose: () => void;
  onRefresh?: () => void;
  /** When true, a frosted overlay covers the iframe for smooth resizing. */
  isDragging?: boolean;
}

export default function PreviewViewer({ url, port, title, onClose, onRefresh, isDragging }: PreviewViewerProps) {
  const [loading, setLoading] = useState(true);
  const [iframeKey, setIframeKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  // Brief delay after drag ends so iframe repaints at new size before overlay lifts
  const [overlayVisible, setOverlayVisible] = useState(false);

  useEffect(() => {
    if (isDragging) {
      setOverlayVisible(true);
    } else if (overlayVisible) {
      const t = setTimeout(() => setOverlayVisible(false), 80);
      return () => clearTimeout(t);
    }
  }, [isDragging, overlayVisible]);

  const handleIframeLoad = useCallback(() => {
    setLoading(false);
  }, []);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    if (onRefresh) {
      onRefresh();
    }
    setIframeKey((k) => k + 1);
  }, [onRefresh]);

  const handleOpenExternal = useCallback(() => {
    window.open(url, '_blank', 'noopener,noreferrer');
  }, [url]);

  const displayTitle = title || 'Preview';
  const hostname = (() => {
    try { return new URL(url).hostname; } catch { return ''; }
  })();

  return (
    <div className="preview-viewer" style={{ position: 'relative' }}>
      <div className="preview-viewer-toolbar">
        <div className="preview-viewer-title">
          <span>{displayTitle}</span>
          <span className="preview-viewer-port-badge">:{port}</span>
        </div>
        <div className="preview-viewer-actions">
          <button className="preview-viewer-btn" onClick={handleRefresh} title="Refresh preview">
            <RefreshCw size={14} />
          </button>
          <button className="preview-viewer-btn" onClick={handleOpenExternal} title="Open in new tab">
            <ExternalLink size={14} />
          </button>
          <button className="preview-viewer-btn" onClick={onClose} title="Close preview">
            <X size={14} />
          </button>
        </div>
      </div>
      {loading && !overlayVisible && (
        <div className="preview-viewer-loading">
          <Loader2 size={24} className="animate-spin" style={{ color: 'var(--color-text-tertiary)' }} />
        </div>
      )}
      {overlayVisible && (
        <div className="preview-viewer-resize-overlay">
          <div className="preview-viewer-resize-card">
            <Globe size={28} style={{ color: 'var(--color-accent-primary)' }} />
            <div className="preview-viewer-resize-info">
              <span className="preview-viewer-resize-title">{displayTitle}</span>
              {hostname && <span className="preview-viewer-resize-url">{hostname}:{port}</span>}
            </div>
          </div>
        </div>
      )}
      <iframe
        ref={iframeRef}
        key={iframeKey}
        src={url}
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        className="preview-viewer-frame"
        title={`Preview - port ${port}`}
        onLoad={handleIframeLoad}
      />
    </div>
  );
}
