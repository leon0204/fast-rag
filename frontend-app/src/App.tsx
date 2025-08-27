import React, { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function App() {
  const [query, setQuery] = useState('docker是什么')
  const [sessionId, setSessionId] = useState('demo')
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
  type ChatMessage = { role: 'user'|'assistant'; content: string; thought?: string }
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const messagesRef = useRef<HTMLDivElement>(null)
  const [expandedThoughts, setExpandedThoughts] = useState<Set<number>>(new Set())
  type HistoryItem = { id: string; title: string; updatedAt: number }
  const [histories, setHistories] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyQuery, setHistoryQuery] = useState('')

  // fetch histories from backend
  async function fetchHistories(q: string = '') {
    if (!API_BASE) return
    setHistoryLoading(true)
    try {
      const url = new URL(`${API_BASE}/history/list`)
      if (q) url.searchParams.set('query', q)
      const resp = await fetch(url.toString())
      if (resp.ok) {
        const data = await resp.json()
        const list: HistoryItem[] = Array.isArray(data) ? data : (data?.items ?? [])
        setHistories(list)
      }
    } catch (_) {
      // ignore; keep current list
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => { fetchHistories('') }, [])

  // debounce search
  useEffect(() => {
    const t = setTimeout(() => { fetchHistories(historyQuery) }, 300)
    return () => clearTimeout(t)
  }, [historyQuery])
  
  // Append streaming chunk without duplicating overlapping suffix/prefix.
  function appendWithoutOverlap(base: string, chunk: string): string {
    if (!chunk) return base
    if (base.endsWith(chunk)) return base
    const max = Math.min(base.length, chunk.length)
    for (let k = max; k > 0; k--) {
      if (base.endsWith(chunk.slice(0, k))) {
        return base + chunk.slice(k)
      }
    }
    return base + chunk
  }

  // no extra normalization; only trim leading spaces per token below

  const scrollToBottom = () => {
    const el = messagesRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  async function send() {
    const q = query.trim()
    if (!q || loading) return

    setMessages(prev => [...prev, { role: 'user', content: q }, { role: 'assistant', content: '', thought: '' }])

    // refresh history list from backend after send (backend stores on request)
    fetchHistories('')
    setQuery('')
    setLoading(true)

    const form = new FormData()
    form.append('query', q)
    if (sessionId) form.append('session_id', sessionId)

    const resp = await fetch(`${API_BASE}/chat/stream`, { method: 'POST', body: form })
    if (!resp.ok || !resp.body) {
      setMessages(prev => {
        const n = [...prev]
        n[n.length - 1] = { role: 'assistant', content: `请求失败: ${resp.status}` }
        return n
      })
      setLoading(false)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          for (const line of rawEvent.split('\n')) {
            if (!line.startsWith('data:')) continue
            const data = line.slice(5).trimStart()
            if (data === '[DONE]') {
              setLoading(false)
              scrollToBottom()
              return
            }
            setMessages(prev => {
              const n = [...prev]
              const last = n[n.length - 1]
              if (last && last.role === 'assistant') {
                // 处理特殊字符 [NEWLINE]，将其转换为实际的换行符
                let processedData = data.replace(/\[NEWLINE\]/g, '\n')
                
                // Capture <think>...</think> into last.thought, others into last.content
                let remaining = processedData
                while (remaining.length > 0) {
                  const startIdx = remaining.indexOf('<think>')
                  const endIdx = remaining.indexOf('</think>')
                  if (startIdx === -1 && endIdx === -1) {
                    last.content = appendWithoutOverlap(last.content, remaining)
                    remaining = ''
                  } else if (startIdx !== -1 && (endIdx === -1 || startIdx < endIdx)) {
                    // append part before <think> to content, then switch to thought mode within this chunk
                    const before = remaining.slice(0, startIdx)
                    if (before) last.content = appendWithoutOverlap(last.content, before)
                    const afterStart = remaining.slice(startIdx + 7)
                    const closeIdx = afterStart.indexOf('</think>')
                    if (closeIdx === -1) {
                      // everything after is thought (open but not closed in this token)
                      last.thought = appendWithoutOverlap(last.thought || '', afterStart)
                      remaining = ''
                    } else {
                      const thoughtSeg = afterStart.slice(0, closeIdx)
                      last.thought = appendWithoutOverlap(last.thought || '', thoughtSeg)
                      remaining = afterStart.slice(closeIdx + 8) // after </think>
                    }
                  } else if (endIdx !== -1) {
                    // there is a stray </think> without a start in this token; treat preceding as thought then close
                    const thoughtSeg = remaining.slice(0, endIdx)
                    if (thoughtSeg) last.thought = appendWithoutOverlap(last.thought || '', thoughtSeg)
                    remaining = remaining.slice(endIdx + 8)
                  } else {
                    // Fallback: append to content
                    last.content = appendWithoutOverlap(last.content, remaining)
                    remaining = ''
                  }
                }
              }
              return n
            })
            scrollToBottom()
          }
        }
      }
    } catch (e: any) {
      setMessages(prev => {
        const n = [...prev]
        const last = n[n.length - 1]
        if (last && last.role === 'assistant') {
          last.content += `\n[流中断: ${e?.message || String(e)}]`
        }
        return n
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`app ${sidebarOpen ? 'with-sidebar' : 'sidebar-collapsed'}`}>
      {!sidebarOpen && (
        <button
          className={`sidebar-toggle closed`}
          aria-label={'打开侧栏'}
          onClick={() => setSidebarOpen(true)}
        >
          <span className="toggle-icon">▦</span>
          <span className="tooltip">打开侧栏</span>
        </button>
      )}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="brand">fastRag</div>
          <button className="collapse" onClick={() => setSidebarOpen(false)} title="折叠">⟨</button>
        </div>
        <div className="sidebar-search">
          <input
            value={historyQuery}
            onChange={e => setHistoryQuery(e.target.value)}
            placeholder="搜索历史..."
          />
        </div>
        <button className="new-chat" onClick={() => {
          const newId = Math.random().toString(36).slice(2, 8)
          setSessionId(newId)
          setMessages([])
        }}>开启新对话</button>
        <div className="history">
          {historyLoading && <div className="history-loading">加载中...</div>}
          {!historyLoading && histories.map(h => (
              <button
                key={h.id}
                className={`history-item ${h.id===sessionId ? 'active': ''}`}
                onClick={() => { setSessionId(h.id); setMessages([]) }}
              >{h.title || h.id}</button>
          ))}
        </div>
      </aside>
      <div className="main">
        <header className="header">
          {!sidebarOpen && (
            <button className="expand" onClick={() => setSidebarOpen(true)} title="展开">☰</button>
          )}
          <span>RAG Chat</span>
        </header>
        <main className="messages" ref={messagesRef}>
        {messages.map((m, i) => {
          if (m.role === 'user') {
            return (
              <div key={i} className={`message user`}>{m.content}</div>
            )
          }
          const expanded = expandedThoughts.has(i)
          return (
            <React.Fragment key={i}>
              {m.thought ? (
                <div className={`thought ${expanded ? 'expanded' : 'collapsed'}`}>
                  <div className="thought-header">
                    <span className="badge">思考中</span>
                    <button
                      className="toggle"
                      onClick={() => {
                        setExpandedThoughts(prev => {
                          const next = new Set(prev)
                          if (next.has(i)) next.delete(i); else next.add(i)
                          return next
                        })
                      }}
                    >{expanded ? '隐藏' : '显示'}</button>
                  </div>
                  {expanded ? (
                    <div className="thought-body">{m.thought}</div>
                  ) : null}
                </div>
              ) : null}
              {m.content && (
                <div className="message assistant">{m.content}</div>
              )}
            </React.Fragment>
          )
        })}
        </main>
        <div className="composer">
          <div className="composer-input">
            <textarea
              rows={1}
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="给 AI 发送消息"
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            />
            <div className="composer-actions">
              <button className="send" onClick={send} disabled={loading} title="发送">↗</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
