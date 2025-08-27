import React, { useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function App() {
  const [query, setQuery] = useState('docker是什么')
  const [sessionId, setSessionId] = useState('demo')
  type ChatMessage = { role: 'user'|'assistant'; content: string; thought?: string }
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const messagesRef = useRef<HTMLDivElement>(null)
  const [expandedThoughts, setExpandedThoughts] = useState<Set<number>>(new Set())
  
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
                // Capture <think>...</think> into last.thought, others into last.content
                let remaining = data
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
    <div className="app">
      <header className="header">RAG Chat</header>
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
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="输入你的问题" />
        <input value={sessionId} onChange={e => setSessionId(e.target.value)} placeholder="会话ID(可选)" />
        <button onClick={send} disabled={loading}>发送</button>
      </div>
    </div>
  )
}
