import { useState, useEffect } from 'react'
import { apiFetch } from '@/lib/api'

interface SettingsData {
  account: {
    wxid: string
    nickname: string
    data_dir: string
    wechat_version: string
  }
  key: {
    status: string
    algorithm: string
    extracted_at: string | null
  }
  cache: {
    fts_index_size: string
    contact_cache_size: string
    last_rebuilt: string | null
  }
  data_directory: {
    path: string
    db_count: number
    total_size: string
  }
}

function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<SettingsData>('/settings')
      .then(setSettings)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page page-settings">
      <h1 className="page-title">设置</h1>

      {loading && <p className="text-muted">加载中...</p>}
      {error && <p className="text-error">加载设置失败: {error}</p>}

      {settings && (
        <div className="settings-sections">
          {/* Account */}
          <section className="settings-card">
            <h2 className="section-title">账号信息</h2>
            <dl className="settings-dl">
              <dt>微信 ID</dt>
              <dd>{settings.account.wxid}</dd>
              <dt>昵称</dt>
              <dd>{settings.account.nickname}</dd>
              <dt>微信版本</dt>
              <dd>{settings.account.wechat_version}</dd>
              <dt>数据目录</dt>
              <dd className="mono">{settings.account.data_dir}</dd>
            </dl>
          </section>

          {/* Key */}
          <section className="settings-card">
            <h2 className="section-title">密钥状态</h2>
            <dl className="settings-dl">
              <dt>状态</dt>
              <dd>
                <span className={`status-badge status-${settings.key.status}`}>
                  {settings.key.status}
                </span>
              </dd>
              <dt>算法</dt>
              <dd>{settings.key.algorithm}</dd>
              <dt>提取时间</dt>
              <dd>{settings.key.extracted_at || '未提取'}</dd>
            </dl>
            <button className="btn btn-secondary" type="button">
              重新提取密钥
            </button>
          </section>

          {/* Cache */}
          <section className="settings-card">
            <h2 className="section-title">缓存</h2>
            <dl className="settings-dl">
              <dt>全文索引大小</dt>
              <dd>{settings.cache.fts_index_size}</dd>
              <dt>联系人缓存</dt>
              <dd>{settings.cache.contact_cache_size}</dd>
              <dt>上次重建</dt>
              <dd>{settings.cache.last_rebuilt || '从未'}</dd>
            </dl>
            <div className="btn-group">
              <button className="btn btn-secondary" type="button">
                重建索引
              </button>
              <button className="btn btn-danger" type="button">
                清空缓存
              </button>
            </div>
          </section>

          {/* Data Directory */}
          <section className="settings-card">
            <h2 className="section-title">数据目录</h2>
            <dl className="settings-dl">
              <dt>路径</dt>
              <dd className="mono">{settings.data_directory.path}</dd>
              <dt>数据库数量</dt>
              <dd>{settings.data_directory.db_count}</dd>
              <dt>总大小</dt>
              <dd>{settings.data_directory.total_size}</dd>
            </dl>
          </section>
        </div>
      )}
    </div>
  )
}

export default Settings
