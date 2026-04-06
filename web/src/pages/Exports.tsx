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
    setExportProgress('正在准备导出...')
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
      setExportProgress('导出中...')
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
      setExportProgress('导出完成')
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败')
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
      <h1 className="page-title">{'导出'}</h1>

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
              <span className="wizard-step-num">{step > s ? '✓' : s}</span>
              <span className="wizard-step-label">
                {s === 1 && '数据来源'}
                {s === 2 && '选择模板'}
                {s === 3 && '格式选项'}
                {s === 4 && '执行导出'}
              </span>
            </div>
          ))}
        </div>

        {/* Step 1: Source selection */}
        {step === 1 && (
          <div className="export-step-content">
            <h3 className="section-title">{'选择数据来源'}</h3>
            <div className="export-source-grid">
              <button
                type="button"
                className={`export-source-card ${source === 'search' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('search')}
              >
                <span className="export-source-icon">{'\�\�'}</span>
                <span className="export-source-name">{'当前搜索'}</span>
                <span className="export-source-desc">{'导出搜索结果'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'workspace' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('workspace')}
              >
                <span className="export-source-icon">{'\�\�'}</span>
                <span className="export-source-name">{'工作区'}</span>
                <span className="export-source-desc">{'导出工作区内容'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'contact' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('contact')}
              >
                <span className="export-source-icon">{'\�\�'}</span>
                <span className="export-source-name">{'联系人'}</span>
                <span className="export-source-desc">{'导出指定联系人的聊天'}</span>
              </button>
              <button
                type="button"
                className={`export-source-card ${source === 'custom' ? 'export-source-selected' : ''}`}
                onClick={() => setSource('custom')}
              >
                <span className="export-source-icon">{'⚙'}</span>
                <span className="export-source-name">{'自定义'}</span>
                <span className="export-source-desc">{'自定义筛选条件'}</span>
              </button>
            </div>

            {/* Source-specific inputs */}
            <div className="export-source-inputs">
              {(source === 'search' || source === 'workspace') && (
                <label className="facet-label">
                  {source === 'search' ? '搜索 ID' : '工作区 ID'}
                  <input
                    type="text"
                    className="facet-input"
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    placeholder={`输入${source === 'search' ? '搜索' : '工作区'} ID...`}
                  />
                </label>
              )}
              {(source === 'contact' || source === 'custom') && (
                <label className="facet-label">
                  {'联系人'}
                  <input
                    type="text"
                    className="facet-input"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder={'输入联系人名称或 wxid...'}
                  />
                </label>
              )}
              {source === 'custom' && (
                <label className="facet-label">
                  {'会话'}
                  <input
                    type="text"
                    className="facet-input"
                    value={conversation}
                    onChange={(e) => setConversation(e.target.value)}
                    placeholder={'输入会话名称...'}
                  />
                </label>
              )}
              {(source === 'contact' || source === 'custom') && (
                <div className="export-date-range">
                  <label className="facet-label">
                    {'开始日期'}
                    <input
                      type="date"
                      className="facet-input"
                      value={since}
                      onChange={(e) => setSince(e.target.value)}
                    />
                  </label>
                  <label className="facet-label">
                    {'结束日期'}
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
              {'下一步: 选择模板'}
            </button>
          </div>
        )}

        {/* Step 2: Template selection */}
        {step === 2 && (
          <div className="export-step-content">
            <h3 className="section-title">{'选择导出模板'}</h3>
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
                {'下一步: 格式选项'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(1)}
              >
                {'上一步'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Format and options */}
        {step === 3 && (
          <div className="export-step-content">
            <h3 className="section-title">{'格式与选项'}</h3>

            <div className="export-format-group">
              <h4 className="col-title">{'输出格式'}</h4>
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
                {'包含附件 (图片\、文件\、视频)'}
              </label>
            </div>

            <label className="facet-label">
              {'输出目录 (可选)'}
              <input
                type="text"
                className="facet-input"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder={'留空使用默认目录...'}
              />
            </label>

            <div className="btn-group" style={{ marginTop: 'var(--space-lg)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setStep(4)}
              >
                {'下一步: 执行导出'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(2)}
              >
                {'上一步'}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Execute */}
        {step === 4 && (
          <div className="export-step-content">
            <h3 className="section-title">{'确认并导出'}</h3>

            <div className="export-summary">
              <dl className="settings-dl">
                <dt>{'来源'}</dt>
                <dd>{source}{sourceId ? ` (${sourceId})` : ''}{contact ? ` - ${contact}` : ''}</dd>
                <dt>{'模板'}</dt>
                <dd>{selectedTemplate || '未选择'}</dd>
                <dt>{'格式'}</dt>
                <dd>{format.toUpperCase()}</dd>
                <dt>{'附件'}</dt>
                <dd>{attachments ? '包含' : '不包含'}</dd>
                {outputDir && (
                  <>
                    <dt>{'输出目录'}</dt>
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
                {exporting ? '导出中...' : '开始导出'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(3)}
                disabled={exporting}
              >
                {'上一步'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Recent Exports (session-only, no backend history) */}
      {recentExports.length > 0 && (
        <section className="recent-section">
          <h2 className="section-title">{'本次会话导出记录'}</h2>
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
