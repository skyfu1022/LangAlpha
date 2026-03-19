import React, { useState, useCallback } from 'react';
import { RefreshCw, ExternalLink, X, Loader2 } from 'lucide-react';
import './PreviewViewer.css';

interface PreviewViewerProps {
  url: string;
  port: number;
  title?: string;
  onClose: () => void;
  onRefresh?: () => void;
}

export default function PreviewViewer({ url, port, title, onClose, onRefresh }: PreviewViewerProps) {
  const [loading, setLoading] = useState(true);
  const [iframeKey, setIframeKey] = useState(0);

  const handleIframeLoad = useCallback(() => {
    setLoading(false);
  }, []);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    if (onRefresh) {
      onRefresh();
    }
    // Force iframe reload via key change
    setIframeKey((k) => k + 1);
  }, [onRefresh]);

  const handleOpenExternal = useCallback(() => {
    window.open(url, '_blank', 'noopener,noreferrer');
  }, [url]);

  const displayTitle = title || `Preview`;

  return (
    <div className="preview-viewer" style={{ position: 'relative' }}>
      <div className="preview-viewer-toolbar">
        <div className="preview-viewer-title">
          <span>{displayTitle}</span>
          <span className="preview-viewer-port-badge">:{port}</span>
        </div>
        <div className="preview-viewer-actions">
          <button
            className="preview-viewer-btn"
            onClick={handleRefresh}
            title="Refresh preview"
          >
            <RefreshCw size={14} />
          </button>
          <button
            className="preview-viewer-btn"
            onClick={handleOpenExternal}
            title="Open in new tab"
          >
            <ExternalLink size={14} />
          </button>
          <button
            className="preview-viewer-btn"
            onClick={onClose}
            title="Close preview"
          >
            <X size={14} />
          </button>
        </div>
      </div>
      {loading && (
        <div className="preview-viewer-loading">
          <Loader2 size={24} className="animate-spin" style={{ color: 'var(--color-text-tertiary)' }} />
        </div>
      )}
      <iframe
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
