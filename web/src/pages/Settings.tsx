import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/api'

interface AccountInfo {
  wxid: string
  path: string
  db_dir: string
  version?: string
}

interface KeyStatusItem {
  wxid: string
  plugin: string
  protection: string
  created_at: string
  last_verified: string
}

interface CacheStatus {
  cache_dir: string
  total_size_bytes: number
  total_size_human: string
  accounts?: Array<Record<string, unknown>>
}

function Settings() {
  const [accounts, setAccounts] = useState<AccountInfo[]>([])
  const [keyStatuses, setKeyStatuses] = useState<KeyStatusItem[]>([])
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [accountsData, keyData, cacheData] = await Promise.allSettled([
        apiFetch<AccountInfo[]>('/accounts'),
        apiFetch<KeyStatusItem[]>('/key/status'),
        apiFetch<CacheStatus>('/cache/status'),
      ])

      if (accountsData.status === 'fulfilled') {
        setAccounts(accountsData.value)
      }
      if (keyData.status === 'fulfilled') {
        setKeyStatuses(keyData.value)
      }
      if (cacheData.status === 'fulfilled') {
        setCacheStatus(cacheData.value)
      }

      const failures = [accountsData, keyData, cacheData].filter(
        (r) => r.status === 'rejected'
      )
      if (failures.length === 3) {
        setError('无法连接到后端服务')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const showAction = (msg: string) => {
    setActionMessage(msg)
    setTimeout(() => setActionMessage(null), 3000)
  }

  const handleVerifyKey = async (account?: string) => {
    setActionLoading('verify-key')
    try {
      const result = await apiFetch<{ account: string; total: number; passed: number; failed: number }>('/key/verify', {
        method: 'POST',
        body: JSON.stringify({ account: account || undefined }),
      })
      if (result.failed === 0) {
        showAction(`密钥验证成功: ${result.passed}/${result.total} 个数据库通过`)
      } else {
        showAction(`密钥验证部分失败: ${result.passed}/${result.total} 通过, ${result.failed} 失败`)
      }
      loadData() // refresh to show updated last_verified
    } catch (err) {
      showAction(`密钥验证失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleBuildIndex = async () => {
    setActionLoading('build-index')
    try {
      await apiFetch('/cache/build-index', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      showAction('索引重建完成')
      loadData()
    } catch (err) {
      showAction(`索引重建失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleClearCache = async () => {
    setActionLoading('clear-cache')
    try {
      await apiFetch('/cache/clear', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      showAction('缓存已清空')
      loadData()
    } catch (err) {
      showAction(`清空缓存失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const firstAccount = accounts.length > 0 ? accounts[0] : null
  const firstKey = keyStatuses.length > 0 ? keyStatuses[0] : null

  return (
    <div className="page page-settings">
      <h1 className="page-title">{'设置'}</h1>

      {loading && <p className="text-muted">{'加载中...'}</p>}
      {error && <p className="text-error">{'加载设置失败'}: {error}</p>}
      {actionMessage && <p className="text-info">{actionMessage}</p>}

      {!loading && (
        <div className="settings-sections">
          {/* Account */}
          <section className="settings-card">
            <h2 className="section-title">{'账号信息'}</h2>
            {firstAccount ? (
              <dl className="settings-dl">
                <dt>{'微信 ID'}</dt>
                <dd>{firstAccount.wxid}</dd>
                {firstAccount.version && (
                  <>
                    <dt>{'微信版本'}</dt>
                    <dd>{firstAccount.version}</dd>
                  </>
                )}
                <dt>{'数据目录'}</dt>
                <dd className="mono">{firstAccount.path}</dd>
                <dt>{'数据库目录'}</dt>
                <dd className="mono">{firstAccount.db_dir}</dd>
              </dl>
            ) : (
              <p className="text-muted">{'未发现账号'}</p>
            )}
            {accounts.length > 1 && (
              <details style={{ marginTop: 'var(--space-md)' }}>
                <summary>{'其他账号'} ({accounts.length - 1})</summary>
                <ul>
                  {accounts.slice(1).map((acc) => (
                    <li key={acc.wxid}>
                      {acc.wxid} ({acc.version || ''})
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>

          {/* Key */}
          <section className="settings-card">
            <h2 className="section-title">{'密钥状态'}</h2>
            {firstKey ? (
              <dl className="settings-dl">
                <dt>{'账号'}</dt>
                <dd>{firstKey.wxid}</dd>
                <dt>{'保护方式'}</dt>
                <dd>
                  <span className={`status-badge status-${firstKey.protection}`}>
                    {firstKey.protection}
                  </span>
                </dd>
                {firstKey.plugin && (
                  <>
                    <dt>{'插件'}</dt>
                    <dd>{firstKey.plugin}</dd>
                  </>
                )}
                {firstKey.created_at && (
                  <>
                    <dt>{'创建时间'}</dt>
                    <dd>{firstKey.created_at}</dd>
                  </>
                )}
                {firstKey.last_verified && (
                  <>
                    <dt>{'上次验证'}</dt>
                    <dd>{firstKey.last_verified}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-muted">{'未发现密钥'}</p>
            )}
            <button
              className="btn btn-secondary"
              type="button"
              disabled={actionLoading === 'verify-key'}
              onClick={() => handleVerifyKey(firstKey?.wxid)}
            >
              {actionLoading === 'verify-key' ? '验证中...' : '验证密钥'}
            </button>
          </section>

          {/* Cache */}
          <section className="settings-card">
            <h2 className="section-title">{'缓存'}</h2>
            {cacheStatus ? (
              <dl className="settings-dl">
                <dt>{'缓存目录'}</dt>
                <dd className="mono">{cacheStatus.cache_dir}</dd>
                {cacheStatus.total_size_human && (
                  <>
                    <dt>{'总大小'}</dt>
                    <dd>{cacheStatus.total_size_human}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-muted">{'无缓存信息'}</p>
            )}
            <div className="btn-group">
              <button
                className="btn btn-secondary"
                type="button"
                disabled={actionLoading === 'build-index'}
                onClick={handleBuildIndex}
              >
                {actionLoading === 'build-index' ? '重建中...' : '重建索引'}
              </button>
              <button
                className="btn btn-danger"
                type="button"
                disabled={actionLoading === 'clear-cache'}
                onClick={handleClearCache}
              >
                {actionLoading === 'clear-cache' ? '清空中...' : '清空缓存'}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default Settings
