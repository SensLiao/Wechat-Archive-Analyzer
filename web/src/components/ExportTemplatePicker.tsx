export interface ExportTemplate {
  id: string
  name: string
  description: string
  icon: string
}

const BUILTIN_TEMPLATES: ExportTemplate[] = [
  {
    id: 'reading-review',
    name: '阅读版聊天回顾',
    description: '生成易读的聊天记录\，按时间线排列\，包含发送者\、时间戳和内容\，适合快速回顾历史对话',
    icon: '\u{1F4D6}',
  },
  {
    id: 'project-timeline',
    name: '项目时间线',
    description: '提取与项目相关的关键消息\，生成时间线视图\，包含里程碑和决策点',
    icon: '\u{1F4C5}',
  },
  {
    id: 'attachment-list',
    name: '附件清单',
    description: '汇总所有文件\、图片\、视频附件\，生成清单并复制到导出目录',
    icon: '\u{1F4CE}',
  },
  {
    id: 'evidence-package',
    name: '证据包',
    description: '生成包含完整元数据的导出包\，适合存档\、举证或合规用途\，包含哈希校验',
    icon: '\u{1F4DC}',
  },
  {
    id: 'raw-structured',
    name: '原始结构化导出',
    description: '导出原始 JSON/CSV 数据\，保留所有字段和元数据\，适合程序化处理或二次开发',
    icon: '\u{1F4BE}',
  },
]

interface ExportTemplatePickerProps {
  selectedTemplate: string | null
  onSelect: (templateId: string) => void
  templates?: ExportTemplate[]
}

function ExportTemplatePicker({
  selectedTemplate,
  onSelect,
  templates,
}: ExportTemplatePickerProps) {
  const displayTemplates = templates && templates.length > 0 ? templates : BUILTIN_TEMPLATES

  return (
    <div className="template-picker">
      <div className="template-grid">
        {displayTemplates.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            className={`template-card ${selectedTemplate === tpl.id ? 'template-card-selected' : ''}`}
            onClick={() => onSelect(tpl.id)}
          >
            <span className="template-icon">{tpl.icon}</span>
            <span className="template-name">{tpl.name}</span>
            <span className="template-desc">{tpl.description}</span>
            {selectedTemplate === tpl.id && (
              <span className="template-check">✓</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

export default ExportTemplatePicker
export { BUILTIN_TEMPLATES }
