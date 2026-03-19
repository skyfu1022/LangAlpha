import React from 'react';
import { Globe, ExternalLink } from 'lucide-react';

const CARD_BG = 'var(--color-bg-tool-card)';
const CARD_BORDER = 'var(--color-border-muted)';
const TEXT_COLOR = 'var(--color-text-tertiary)';
const ACCENT = 'var(--color-accent-primary)';

interface InlinePreviewCardProps {
  artifact: Record<string, unknown> | null | undefined;
  onClick?: () => void;
}

export function InlinePreviewCard({ artifact, onClick }: InlinePreviewCardProps): React.ReactElement | null {
  if (!artifact) return null;

  const port = artifact.port as number | undefined;
  const title = (artifact.title as string) || (port ? `Port ${port}` : 'Preview');

  return (
    <div
      style={{
        background: CARD_BG,
        border: `1px solid ${CARD_BORDER}`,
        borderRadius: 8,
        padding: '10px 14px',
        cursor: 'pointer',
        transition: 'border-color 0.15s',
        outline: 'none',
        WebkitTapHighlightColor: 'transparent',
        userSelect: 'none',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
      onClick={onClick}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = ACCENT)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = CARD_BORDER)}
    >
      <Globe size={16} style={{ color: ACCENT, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)', fontSize: 13 }}>
            {title}
          </span>
          {port && (
            <span
              style={{
                fontSize: 10,
                fontFamily: 'var(--font-mono, monospace)',
                padding: '1px 6px',
                borderRadius: 10,
                backgroundColor: 'var(--color-bg-surface)',
                color: TEXT_COLOR,
              }}
            >
              :{port}
            </span>
          )}
        </div>
        <div style={{ fontSize: 11, color: TEXT_COLOR, marginTop: 1 }}>
          Click to open preview
        </div>
      </div>
      <ExternalLink size={14} style={{ color: TEXT_COLOR, flexShrink: 0 }} />
    </div>
  );
}
