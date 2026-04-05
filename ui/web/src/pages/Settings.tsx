import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/api'

interface AccountInfo {
  wxid: string
  nickname: string
  data_dir: string
  wechat_version?: string
  db_count?: number
}

interface KeyStatusItem {
  account: string
  status: string
  algorithm?: string
  extracted_at?: string | null
}

interface CacheStatus {
  cache_dir: string
  total_size?: string
  accounts?: Record<string, unknown>
  [key: string]: unknown
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
        setError('\u65E0\u6CD5\u8FDE\u63A5\u5230\u540E\u7AEF\u670D\u52A1')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '\u52A0\u8F7D\u5931\u8D25')
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
      const result = await apiFetch<{ valid: boolean; message?: string }>('/key/verify', {
        method: 'POST',
        body: JSON.stringify({ account: account || undefined }),
      })
      showAction(result.valid ? '\u5BC6\u94A5\u9A8C\u8BC1\u6210\u529F' : `\u5BC6\u94A5\u9A8C\u8BC1\u5931\u8D25: ${result.message || '\u672A\u77E5\u9519\u8BEF'}`)
    } catch (err) {
      showAction(`\u5BC6\u94A5\u9A8C\u8BC1\u5931\u8D25: ${err instanceof Error ? err.message : '\u672A\u77E5\u9519\u8BEF'}`)
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
      showAction('\u7D22\u5F15\u91CD\u5EFA\u5B8C\u6210')
      loadData()
    } catch (err) {
      showAction(`\u7D22\u5F15\u91CD\u5EFA\u5931\u8D25: ${err instanceof Error ? err.message : '\u672A\u77E5\u9519\u8BEF'}`)
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
      showAction('\u7F13\u5B58\u5DF2\u6E05\u7A7A')
      loadData()
    } catch (err) {
      showAction(`\u6E05\u7A7A\u7F13\u5B58\u5931\u8D25: ${err instanceof Error ? err.message : '\u672A\u77E5\u9519\u8BEF'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const firstAccount = accounts.length > 0 ? accounts[0] : null
  const firstKey = keyStatuses.length > 0 ? keyStatuses[0] : null

  return (
    <div className="page page-settings">
      <h1 className="page-title">{'\u8BBE\u7F6E'}</h1>

      {loading && <p className="text-muted">{'\u52A0\u8F7D\u4E2D...'}</p>}
      {error && <p className="text-error">{'\u52A0\u8F7D\u8BBE\u7F6E\u5931\u8D25'}: {error}</p>}
      {actionMessage && <p className="text-info">{actionMessage}</p>}

      {!loading && (
        <div className="settings-sections">
          {/* Account */}
          <section className="settings-card">
            <h2 className="section-title">{'\u8D26\u53F7\u4FE1\u606F'}</h2>
            {firstAccount ? (
              <dl className="settings-dl">
                <dt>{'\u5FAE\u4FE1 ID'}</dt>
                <dd>{firstAccount.wxid}</dd>
                <dt>{'\u6635\u79F0'}</dt>
                <dd>{firstAccount.nickname}</dd>
                {firstAccount.wechat_version && (
                  <>
                    <dt>{'\u5FAE\u4FE1\u7248\u672C'}</dt>
                    <dd>{firstAccount.wechat_version}</dd>
                  </>
                )}
                <dt>{'\u6570\u636E\u76EE\u5F55'}</dt>
                <dd className="mono">{firstAccount.data_dir}</dd>
                {firstAccount.db_count !== undefined && (
                  <>
                    <dt>{'\u6570\u636E\u5E93\u6570\u91CF'}</dt>
                    <dd>{firstAccount.db_count}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-muted">{'\u672A\u53D1\u73B0\u8D26\u53F7'}</p>
            )}
            {accounts.length > 1 && (
              <details style={{ marginTop: 'var(--space-md)' }}>
                <summary>{'\u5176\u4ED6\u8D26\u53F7'} ({accounts.length - 1})</summary>
                <ul>
                  {accounts.slice(1).map((acc) => (
                    <li key={acc.wxid}>
                      {acc.nickname} ({acc.wxid})
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>

          {/* Key */}
          <section className="settings-card">
            <h2 className="section-title">{'\u5BC6\u94A5\u72B6\u6001'}</h2>
            {firstKey ? (
              <dl className="settings-dl">
                <dt>{'\u8D26\u53F7'}</dt>
                <dd>{firstKey.account}</dd>
                <dt>{'\u72B6\u6001'}</dt>
                <dd>
                  <span className={`status-badge status-${firstKey.status}`}>
                    {firstKey.status}
                  </span>
                </dd>
                {firstKey.algorithm && (
                  <>
                    <dt>{'\u7B97\u6CD5'}</dt>
                    <dd>{firstKey.algorithm}</dd>
                  </>
                )}
                {firstKey.extracted_at && (
                  <>
                    <dt>{'\u63D0\u53D6\u65F6\u95F4'}</dt>
                    <dd>{firstKey.extracted_at}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-muted">{'\u672A\u53D1\u73B0\u5BC6\u94A5'}</p>
            )}
            <button
              className="btn btn-secondary"
              type="button"
              disabled={actionLoading === 'verify-key'}
              onClick={() => handleVerifyKey(firstKey?.account)}
            >
              {actionLoading === 'verify-key' ? '\u9A8C\u8BC1\u4E2D...' : '\u9A8C\u8BC1\u5BC6\u94A5'}
            </button>
          </section>

          {/* Cache */}
          <section className="settings-card">
            <h2 className="section-title">{'\u7F13\u5B58'}</h2>
            {cacheStatus ? (
              <dl className="settings-dl">
                <dt>{'\u7F13\u5B58\u76EE\u5F55'}</dt>
                <dd className="mono">{cacheStatus.cache_dir}</dd>
                {cacheStatus.total_size && (
                  <>
                    <dt>{'\u603B\u5927\u5C0F'}</dt>
                    <dd>{cacheStatus.total_size}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-muted">{'\u65E0\u7F13\u5B58\u4FE1\u606F'}</p>
            )}
            <div className="btn-group">
              <button
                className="btn btn-secondary"
                type="button"
                disabled={actionLoading === 'build-index'}
                onClick={handleBuildIndex}
              >
                {actionLoading === 'build-index' ? '\u91CD\u5EFA\u4E2D...' : '\u91CD\u5EFA\u7D22\u5F15'}
              </button>
              <button
                className="btn btn-danger"
                type="button"
                disabled={actionLoading === 'clear-cache'}
                onClick={handleClearCache}
              >
                {actionLoading === 'clear-cache' ? '\u6E05\u7A7A\u4E2D...' : '\u6E05\u7A7A\u7F13\u5B58'}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default Settings
