import { useState } from 'react'

const BASE_URL = 'http://localhost:8000'

interface LogSummary {
  id: number
  session_id: string
  first_question: string
  created_at: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface LogDetail {
  session_id: string
  first_question: string
  created_at: string
  messages: Message[]
}

function formatTime(isoStr: string): string {
  const d = new Date(isoStr)
  const yy = String(d.getFullYear()).slice(2)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${yy}/${mm}/${dd} ${hh}:${min}`
}

export default function AdminDashboard() {
  const [adminKey, setAdminKey] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [logs, setLogs] = useState<LogSummary[]>([])
  const [selected, setSelected] = useState<LogDetail | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // 모바일: 'list' | 'detail'
  const [mobileView, setMobileView] = useState<'list' | 'detail'>('list')

  const authenticate = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${BASE_URL}/admin/logs`, {
        headers: { 'X-Admin-Key': adminKey },
      })
      if (res.status === 401) {
        setError('인증 실패: 관리자 키를 확인하세요.')
        return
      }
      const data = await res.json()
      setLogs(data)
      setAuthenticated(true)
    } catch {
      setError('서버 연결 실패')
    } finally {
      setLoading(false)
    }
  }

  const loadDetail = async (session_id: string) => {
    try {
      const res = await fetch(`${BASE_URL}/admin/logs/${session_id}`, {
        headers: { 'X-Admin-Key': adminKey },
      })
      const data = await res.json()
      setSelected(data)
      setMobileView('detail')
    } catch {
      setError('대화 내역 로드 실패')
    }
  }

  const deleteLog = async (session_id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('이 대화 로그를 삭제할까요?')) return
    try {
      await fetch(`${BASE_URL}/admin/logs/${session_id}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Key': adminKey },
      })
      setLogs((prev) => prev.filter((l) => l.session_id !== session_id))
      if (selected?.session_id === session_id) {
        setSelected(null)
        setMobileView('list')
      }
    } catch {
      setError('삭제 실패')
    }
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-kb-gray flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-sm p-6 w-full max-w-sm">
          <div className="flex items-center gap-3 mb-6">
            <img src="/logo.png" alt="KB" className="h-7" />
            <span className="font-display font-medium text-kb-navy">관리자 대시보드</span>
          </div>
          <input
            type="password"
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-kb-yellow"
            placeholder="관리자 키 입력"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && authenticate()}
          />
          {error && <p className="text-xs text-red-500 mb-3">{error}</p>}
          <button
            className="w-full bg-kb-yellow text-kb-navy font-medium rounded-xl py-2.5 text-sm hover:bg-kb-yellow-dark transition-colors disabled:opacity-50"
            onClick={authenticate}
            disabled={loading || !adminKey}
          >
            {loading ? '확인 중...' : '로그인'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-kb-gray">
      {/* 헤더 */}
      <header className="bg-kb-yellow px-4 py-3 flex items-center gap-3 shadow-sm">
        {/* 모바일 상세 화면에서 뒤로가기 */}
        {mobileView === 'detail' && (
          <button
            className="md:hidden text-kb-navy mr-1"
            onClick={() => setMobileView('list')}
            aria-label="목록으로"
          >
            ←
          </button>
        )}
        <img src="/logo.png" alt="KB" className="h-7" />
        <span className="font-display font-medium text-kb-navy truncate">
          {mobileView === 'detail' && selected
            ? <span className="text-sm">{selected.first_question.slice(0, 20)}...</span>
            : '대화 로그 대시보드'}
        </span>
      </header>

      <div className="flex h-[calc(100vh-52px)]">
        {/* 세션 목록 - 모바일: mobileView==='list'일 때만, 데스크톱: 항상 */}
        <div className={`
          w-full md:w-80 bg-white border-r border-gray-100 overflow-y-auto flex-shrink-0
          ${mobileView === 'detail' ? 'hidden md:block' : 'block'}
        `}>
          {logs.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">대화 내역이 없습니다.</p>
          ) : (
            <>
              <p className="text-xs text-gray-400 px-4 py-2 border-b border-gray-100">
                총 {logs.length}개 세션
              </p>
              {logs.map((log) => (
              <button
                key={log.session_id}
                className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-kb-yellow-light transition-colors ${
                  selected?.session_id === log.session_id ? 'bg-kb-yellow-light border-l-2 border-l-kb-yellow' : ''
                }`}
                onClick={() => loadDetail(log.session_id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-kb-navy font-medium line-clamp-2 mb-1">
                      {log.first_question}
                    </p>
                    <p className="text-xs text-gray-400">{formatTime(log.created_at)}</p>
                  </div>
                  <button
                    className="flex-shrink-0 text-gray-300 hover:text-red-400 transition-colors text-lg leading-none mt-0.5"
                    onClick={(e) => deleteLog(log.session_id, e)}
                    aria-label="로그 삭제"
                  >
                    ×
                  </button>
                </div>
              </button>
            ))}
            </>
          )}
        </div>

        {/* 대화 상세 - 모바일: mobileView==='detail'일 때만, 데스크톱: 항상 */}
        <div className={`
          flex-1 overflow-y-auto p-4
          ${mobileView === 'list' ? 'hidden md:block' : 'block'}
        `}>
          {!selected ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              왼쪽 목록에서 세션을 선택하세요.
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-3">
              <p className="text-xs text-gray-400 mb-4">
                {formatTime(selected.created_at)}
              </p>
              {selected.messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-6 h-6 rounded-full bg-kb-yellow flex items-center justify-center mr-2 flex-shrink-0 mt-1">
                      <span className="text-xs font-bold text-kb-navy">AI</span>
                    </div>
                  )}
                  <div className="flex flex-col items-end max-w-[85%]">
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap w-full ${
                        msg.role === 'user'
                          ? 'bg-[#FFB800] text-gray-900 rounded-br-sm'
                          : 'bg-white text-gray-900 rounded-bl-sm shadow-sm'
                      }`}
                    >
                      {msg.content}
                    </div>
                    {msg.role === 'user' && (
                      <span className="text-xs text-gray-400 mt-1 mr-1">
                        {formatTime(selected.created_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
