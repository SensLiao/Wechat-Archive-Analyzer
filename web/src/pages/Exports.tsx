import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'
import ExportTemplatePicker from '@/components/ExportTemplatePicker'
import type { ExportTemplate } from '@/components/ExportTemplatePicker'
import RecentExports from '@/components/RecentExports'
import type { ExportRecord } from '@/components/RecentExports'

type ExportSource = 'search' | 'workspace' | 'contact' | 'custom'
type ExportFormat = 'html' | 'csv' | 'json'

/** Maps frontend source concepts to backend surface values. */
const SOURCE_TO_SURFACE: Record<ExportSource, string> = {
  search: 'chat',
  workspace: 'chat',
  contact: 'chat',
  custom: 'all',
}

interface BackendExportResponse {
  total_messages: number
  total_conversations: number
  files: string[]
  output_dir: string
  format: string
}

function Exports() {
  // Wizard step: 1=source, 2=template, 3=format, 4=export
  const [step, setStep] = useState(1)

  // Step 1: Source
  const [source, setSource] = useState<ExportSource>('search')
  const [sourceId, setSourceId] = useState('')
  const [contact, setContact] = useState('')
  const [conversation, setConversation] = useState('')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')

  // Step 2: Template
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [serverTemplates, setServerTemplates] = useState<ExportTemplate[]>([])

  // Step 3: Format
  const [format, setFormat] = useState<ExportFormat>('html')
  const [attachments, setAttachments] = useState(false)
  const [outputDir, setOutputDir] = useState('')

  // Step 4: Export state
  const [exporting, setExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState<string | null>(null)

  // Session-only recent exports (no backend history endpoint)
  const [recentExports, setRecentExports] = useState<ExportRecord[]>([])
  const [error, setError] = useState<string | null>(null)

  // Read URL params for pre-filled source
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlSource = params.get('source')
    const urlSourceId = params.get('source_id')
    if (urlSource && ['search', 'workspace', 'contact', 'custom'].includes(urlSource)) {
      setSource(urlSource as ExportSource)
      if (urlSourceId) setSourceId(urlSourceId)
      setStep(2) // skip to template if source is pre-filled
    }
  }, [])

  // Load server templates
  useEffect(() => {
    apiFetch<{ templates: ExportTemplate[] }>('/export/templates')
      .then((data) => setServerTemplates(data.templates))
      .catch(() => { /* use built-in templates */ })
  }, [])

  const handleExport = async () => {
    setExporting(true)
    setExportProgress('\u6B63\u5728\u51C6\u5907\u5BFC\u51FA...')
    setError(null)

    const body: Record<string, unknown> = {
      format,
      output_dir: outputDir || undefined,
      template: selectedTemplate || undefined,
      attachments: attachments ? 'copy' : undefined,
      surface: SOURCE_TO_SURFACE[source],
    }

    if (source === 'contact') {
      body.contact = contact || undefined
    } else if (source === 'workspace') {
      body.conversation = sourceId || undefined
    } else if (source === 'custom') {
      body.contact = contact || undefined
      body.conversation = conversation || undefined
    }

    if (since) body.since = since
    if (until) body.until = until

    try {
      setExportProgress('\u5BFC\u51FA\u4E2D...')
      const result = await apiFetch<BackendExportResponse>('/export', {
        method: 'POST',
        body: JSON.stringify(body),
      })

      const newRecord: ExportRecord = {
        id: `export-${Date.now()}`,
        template: selectedTemplate || undefined,
        format: result.format,
        source,
        record_count: result.total_messages,
        file_count: result.files.length,
        created: new Date().toLocaleString(),
        status: 'completed',
        output_dir: result.output_dir,
      }
      setRecentExports((prev) => [newRecord, ...prev])
      setExportProgress('\u5BFC\u51FA\u5B8C\u6210')
    } catch (err) {
      setError(err instanceof Error ? err.message : '\u5BFC\u51FA\u5931\u8D25')
      setExportProgress(null)
    } finally {
      setExporting(false)
    }
  }

  const handleReExport = (record: ExportRecord) => {
    if (record.template) setSelectedTemplate(record.template)
    setFormat(record.format as ExportFormat)
    setStep(3)
  }

  const canProceedStep1 = source === 'search' || source === 'workspace'
    ? sourceId.trim().length > 0
    : source === 'contact'
      ? contact.trim().length > 0
      : true

  const canProceedStep2 = selectedTemplate !== null

  return (
    <div className="page page-exports">
      <h1 className="page-title">{'\u5BFC\u51FA'}</h1>

      {error && <p className="text-error">{error}</p>}

      {/* Step wizard */}
      <div className="export-wizard">
        {/* Step indicators */}
        <div className="wizard-steps">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`wizard-step-indicator ${step === s ? 'wizard-step-active' : ''} ${step > s ? 'wizard-step-done' : ''}`}
              onClick={() => { if (s < step) setStep(s) }}
            >
              <span className="wizard-step-num">{step > s ? '\u2713' : s}</span>
              <span className="wizard-step-label">
                {s === 1 && '\u6570\u636E\u6765\u6E90'}
                {s === 2 && '\u9009\u62E9\u6A21\u677F'}
                {s === 3 && '\u683C\u5F0F\u9009\u9879'}
                {s === 4 && '\u6267\u884C\u5BFC\u51FA'}
              </span>
            </div>
          ))}
        </div>

        {/* Step 1: Source selection */}
        {step === 1 && (
          <div className="export-step-content">
            <h3 className="section-title">{'\u9009\u62E9\u6570\u636E\u6765\u6E90'}</h3>
            <div className="export-source-grid">
              <button
                type="button"
                className={`export-source-card ${source === 'search' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('search')}
              >
                <span className="export-source-icon">{'\ud83d\udd0d'}</span>
                <span className="export-source-name">{'\u5F53\u524D\u641C\u7D22'}</span>
                <span className="export-source-desc">{'\u5BFC\u51FA\u641C\u7D22\u7ED3\u679C'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'workspace' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('workspace')}
              >
                <span className="export-source-icon">{'\ud83d\udcc1'}</span>
                <span className="export-source-name">{'\u5DE5\u4F5C\u533A'}</span>
                <span className="export-source-desc">{'\u5BFC\u51FA\u5DE5\u4F5C\u533A\u5185\u5BB9'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'contact' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('contact')}
              >
                <span className="export-source-icon">{'\ud83d\udc64'}</span>
                <span className="export-source-name">{'\u8054\u7CFB\u4EBA'}</span>
                <span className="export-source-desc">{'\u5BFC\u51FA\u6307\u5B9A\u8054\u7CFB\u4EBA\u7684\u804A\u5929'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'custom' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('custom')}
              >
                <span className="export-source-icon">{'\u2699'}</span>
                <span className="export-source-name">{'\u81EA\u5B9A\u4E49'}</span>
                <span className="export-source-desc">{'\u81EA\u5B9A\u4E49\u7B5B\u9009\u6761\u4EF6'}</span>
              </button>
            </div>

            {/* Source-specific inputs */}
            <div className="export-source-inputs">
              {(source === 'search' || source === 'workspace') && (
                <label className="facet-label">
                  {source === 'search' ? '\u641C\u7D22 ID' : '\u5DE5\u4F5C\u533A ID'}
                  <input
                    type="text"
                    className="facet-input"
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    placeholder={`\u8F93\u5165${source === 'search' ? '\u641C\u7D22' : '\u5DE5\u4F5C\u533A'} ID...`}
                  />
                </label>
              )}
              {(source === 'contact' || source === 'custom') && (
                <label className="facet-label">
                  {'\u8054\u7CFB\u4EBA'}
                  <input
                    type="text"
                    className="facet-input"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder={'\u8F93\u5165\u8054\u7CFB\u4EBA\u540D\u79F0\u6216 wxid...'}
                  />
                </label>
              )}
              {source === 'custom' && (
                <label className="facet-label">
                  {'\u4F1A\u8BDD'}
                  <input
                    type="text"
                    className="facet-input"
                    value={conversation}
                    onChange={(e) => setConversation(e.target.value)}
                    placeholder={'\u8F93\u5165\u4F1A\u8BDD\u540D\u79F0...'}
                  />
                </label>
              )}
              {(source === 'contact' || source === 'custom') && (
                <div className="export-date-range">
                  <label className="facet-label">
                    {'\u5F00\u59CB\u65E5\u671F'}
                    <input
                      type="date"
                      className="facet-input"
                      value={since}
                      onChange={(e) => setSince(e.target.value)}
                    />
                  </label>
                  <label className="facet-label">
                    {'\u7ED3\u675F\u65E5\u671F'}
                    <input
                      type="date"
                      className="facet-input"
                      value={until}
                      onChange={(e) => setUntil(e.target.value)}
                    />
                  </label>
                </div>
              )}
            </div>

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep(2)}
              disabled={!canProceedStep1}
            >
              {'\u4E0B\u4E00\u6B65: \u9009\u62E9\u6A21\u677F'}
            </button>
          </div>
        )}

        {/* Step 2: Template selection */}
        {step === 2 && (
          <div className="export-step-content">
            <h3 className="section-title">{'\u9009\u62E9\u5BFC\u51FA\u6A21\u677F'}</h3>
            <ExportTemplatePicker
              selectedTemplate={selectedTemplate}
              onSelect={setSelectedTemplate}
              templates={serverTemplates.length > 0 ? serverTemplates : undefined}
            />
            <div className="btn-group" style={{ marginTop: 'var(--space-lg)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setStep(3)}
                disabled={!canProceedStep2}
              >
                {'\u4E0B\u4E00\u6B65: \u683C\u5F0F\u9009\u9879'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(1)}
              >
                {'\u4E0A\u4E00\u6B65'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Format and options */}
        {step === 3 && (
          <div className="export-step-content">
            <h3 className="section-title">{'\u683C\u5F0F\u4E0E\u9009\u9879'}</h3>

            <div className="export-format-group">
              <h4 className="col-title">{'\u8F93\u51FA\u683C\u5F0F'}</h4>
              <div className="radio-group">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="format"
                    value="html"
                    checked={format === 'html'}
                    onChange={() => setFormat('html')}
                  />
                  HTML
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="format"
                    value="csv"
                    checked={format === 'csv'}
                    onChange={() => setFormat('csv')}
                  />
                  CSV
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="format"
                    value="json"
                    checked={format === 'json'}
                    onChange={() => setFormat('json')}
                  />
                  JSON
                </label>
              </div>
            </div>

            <div className="export-options">
              <label className="radio-label">
                <input
                  type="checkbox"
                  checked={attachments}
                  onChange={(e) => setAttachments(e.target.checked)}
                />
                {'\u5305\u542B\u9644\u4EF6 (\u56FE\u7247\u3001\u6587\u4EF6\u3001\u89C6\u9891)'}
              </label>
            </div>

            <label className="facet-label">
              {'\u8F93\u51FA\u76EE\u5F55 (\u53EF\u9009)'}
              <input
                type="text"
                className="facet-input"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder={'\u7559\u7A7A\u4F7F\u7528\u9ED8\u8BA4\u76EE\u5F55...'}
              />
            </label>

            <div className="btn-group" style={{ marginTop: 'var(--space-lg)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setStep(4)}
              >
                {'\u4E0B\u4E00\u6B65: \u6267\u884C\u5BFC\u51FA'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(2)}
              >
                {'\u4E0A\u4E00\u6B65'}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Execute */}
        {step === 4 && (
          <div className="export-step-content">
            <h3 className="section-title">{'\u786E\u8BA4\u5E76\u5BFC\u51FA'}</h3>

            <div className="export-summary">
              <dl className="settings-dl">
                <dt>{'\u6765\u6E90'}</dt>
                <dd>{source}{sourceId ? ` (${sourceId})` : ''}{contact ? ` - ${contact}` : ''}</dd>
                <dt>{'\u6A21\u677F'}</dt>
                <dd>{selectedTemplate || '\u672A\u9009\u62E9'}</dd>
                <dt>{'\u683C\u5F0F'}</dt>
                <dd>{format.toUpperCase()}</dd>
                <dt>{'\u9644\u4EF6'}</dt>
                <dd>{attachments ? '\u5305\u542B' : '\u4E0D\u5305\u542B'}</dd>
                {outputDir && (
                  <>
                    <dt>{'\u8F93\u51FA\u76EE\u5F55'}</dt>
                    <dd className="mono">{outputDir}</dd>
                  </>
                )}
              </dl>
            </div>

            {exportProgress && (
              <p className="export-progress-text">{exportProgress}</p>
            )}

            <div className="btn-group" style={{ marginTop: 'var(--space-lg)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleExport}
                disabled={exporting}
              >
                {exporting ? '\u5BFC\u51FA\u4E2D...' : '\u5F00\u59CB\u5BFC\u51FA'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(3)}
                disabled={exporting}
              >
                {'\u4E0A\u4E00\u6B65'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Recent Exports (session-only, no backend history) */}
      {recentExports.length > 0 && (
        <section className="recent-section">
          <h2 className="section-title">{'\u672C\u6B21\u4F1A\u8BDD\u5BFC\u51FA\u8BB0\u5F55'}</h2>
          <RecentExports
            exports={recentExports}
            loading={false}
            onReExport={handleReExport}
          />
        </section>
      )}
    </div>
  )
}

export default Exports
