export interface ExportTemplate {
  id: string
  name: string
  description: string
  icon: string
}

const BUILTIN_TEMPLATES: ExportTemplate[] = [
  {
    id: 'reading-review',
    name: '\u9605\u8BFB\u7248\u804A\u5929\u56DE\u987E',
    description: '\u751F\u6210\u6613\u8BFB\u7684\u804A\u5929\u8BB0\u5F55\uFF0C\u6309\u65F6\u95F4\u7EBF\u6392\u5217\uFF0C\u5305\u542B\u53D1\u9001\u8005\u3001\u65F6\u95F4\u6233\u548C\u5185\u5BB9\uFF0C\u9002\u5408\u5FEB\u901F\u56DE\u987E\u5386\u53F2\u5BF9\u8BDD',
    icon: '\u{1F4D6}',
  },
  {
    id: 'project-timeline',
    name: '\u9879\u76EE\u65F6\u95F4\u7EBF',
    description: '\u63D0\u53D6\u4E0E\u9879\u76EE\u76F8\u5173\u7684\u5173\u952E\u6D88\u606F\uFF0C\u751F\u6210\u65F6\u95F4\u7EBF\u89C6\u56FE\uFF0C\u5305\u542B\u91CC\u7A0B\u7891\u548C\u51B3\u7B56\u70B9',
    icon: '\u{1F4C5}',
  },
  {
    id: 'attachment-list',
    name: '\u9644\u4EF6\u6E05\u5355',
    description: '\u6C47\u603B\u6240\u6709\u6587\u4EF6\u3001\u56FE\u7247\u3001\u89C6\u9891\u9644\u4EF6\uFF0C\u751F\u6210\u6E05\u5355\u5E76\u590D\u5236\u5230\u5BFC\u51FA\u76EE\u5F55',
    icon: '\u{1F4CE}',
  },
  {
    id: 'evidence-package',
    name: '\u8BC1\u636E\u5305',
    description: '\u751F\u6210\u5305\u542B\u5B8C\u6574\u5143\u6570\u636E\u7684\u5BFC\u51FA\u5305\uFF0C\u9002\u5408\u5B58\u6863\u3001\u4E3E\u8BC1\u6216\u5408\u89C4\u7528\u9014\uFF0C\u5305\u542B\u54C8\u5E0C\u6821\u9A8C',
    icon: '\u{1F4DC}',
  },
  {
    id: 'raw-structured',
    name: '\u539F\u59CB\u7ED3\u6784\u5316\u5BFC\u51FA',
    description: '\u5BFC\u51FA\u539F\u59CB JSON/CSV \u6570\u636E\uFF0C\u4FDD\u7559\u6240\u6709\u5B57\u6BB5\u548C\u5143\u6570\u636E\uFF0C\u9002\u5408\u7A0B\u5E8F\u5316\u5904\u7406\u6216\u4E8C\u6B21\u5F00\u53D1',
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
              <span className="template-check">\u2713</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

export default ExportTemplatePicker
export { BUILTIN_TEMPLATES }
