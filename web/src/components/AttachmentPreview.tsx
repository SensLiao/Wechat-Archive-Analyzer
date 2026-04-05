interface Attachment {
  type: 'image' | 'video' | 'audio' | 'file'
  filename: string
  size?: number
  url?: string
  thumbnail?: string
}

interface AttachmentPreviewProps {
  attachment: Attachment
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getFileIcon(type: Attachment['type']): string {
  switch (type) {
    case 'image': return '\u{1F5BC}'
    case 'video': return '\u{1F3AC}'
    case 'audio': return '\u{1F3B5}'
    case 'file': return '\u{1F4CE}'
  }
}

function AttachmentPreview({ attachment }: AttachmentPreviewProps) {
  const { type, filename, size, url, thumbnail } = attachment

  return (
    <div className="attachment-preview">
      {type === 'image' && (thumbnail || url) ? (
        <div className="attachment-preview__image">
          <img
            src={thumbnail || url}
            alt={filename}
            loading="lazy"
          />
        </div>
      ) : (
        <div className="attachment-preview__icon">
          <span className="attachment-preview__emoji">{getFileIcon(type)}</span>
        </div>
      )}
      <div className="attachment-preview__info">
        <span className="attachment-preview__name" title={filename}>
          {filename}
        </span>
        {size != null && (
          <span className="attachment-preview__size">{formatSize(size)}</span>
        )}
      </div>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary attachment-preview__open"
        >
          Open file
        </a>
      )}
    </div>
  )
}

export type { Attachment }
export default AttachmentPreview
