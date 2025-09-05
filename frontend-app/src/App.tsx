import React, { useEffect, useRef, useState } from 'react'
import KnowledgeBase from './KnowledgeBase'
import LangGraphTrace from './LangGraphTrace'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export default function App() {
  const [query, setQuery] = useState('docker是什么')
  const [sessionId, setSessionId] = useState('demo')
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
  type ChatMessage = { role: 'user'|'assistant'; content: string; thought?: string }
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const messagesRef = useRef<HTMLDivElement>(null)
  const [expandedThoughts, _setExpandedThoughts] = useState<Set<number>>(new Set())
  type HistoryItem = { 
    id: string; 
    title: string; 
    updatedAt?: number;
    message_count?: number;
    updated_at?: string;
  }
  const [histories, setHistories] = useState<HistoryItem[]>([])
  const [highlightedSessions, setHighlightedSessions] = useState<Set<string>>(new Set())
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyQuery, setHistoryQuery] = useState('')
  
  
  // 模型切换相关状态
  const [currentModel, setCurrentModel] = useState('')
  const [showModelSelector, setShowModelSelector] = useState(false)
  const [_modelSwitchMessage, setModelSwitchMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  
  // LangGraph轨迹相关状态
  const [langgraphTrace, setLanggraphTrace] = useState<any>(null)
  const [traceStorage, setTraceStorage] = useState<Record<string, any>>({})
  
  // 模型配置
  const models = [
    {
      id: 'ollama',
      name: 'Ollama',
      description: '本地部署，快速响应',
      icon: '🦙'
    },
    {
      id: 'deepseek',
      name: 'DeepSeek',
      description: '云端AI，深度思考',
      icon: '🚀'
    }
  ]

  // 切换模型函数
  async function switchModel(modelId: string) {
    try {
      const response = await fetch(`${API_BASE}/manage/model/switch?model_type=${modelId}`, {
        method: 'POST'
      })
      if (response.ok) {
        const result = await response.json()
        // 更新当前模型名称
        const modelName = models.find(m => m.id === modelId)?.name || modelId
        setCurrentModel(modelName)
        // 显示成功提示
        setModelSwitchMessage({
          type: 'success',
          text: `模型切换成功: ${result.message}`
        })
        // 3秒后自动清除提示
        setTimeout(() => {
          setModelSwitchMessage(null)
        }, 3000)
        console.log(`模型已切换到: ${modelId}`)
      } else {
        const errorData = await response.json()
        setModelSwitchMessage({
          type: 'error',
          text: `模型切换失败: ${errorData.detail || '未知错误'}`
        })
        // 5秒后自动清除错误提示
        setTimeout(() => {
          setModelSwitchMessage(null)
        }, 5000)
        console.error('模型切换失败')
      }
    } catch (error) {
      setModelSwitchMessage({
        type: 'error',
        text: `模型切换出错: ${error}`
      })
      // 5秒后自动清除错误提示
      setTimeout(() => {
        setModelSwitchMessage(null)
      }, 5000)
      console.error('模型切换出错:', error)
    }
  }

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
        // 计算变化的会话（新会话或更新时间/消息数变化）
        const prevMap = new Map(histories.map(h => [h.id, h]))
        const changed = new Set<string>()
        for (const h of list) {
          const prev = prevMap.get(h.id)
          if (!prev || prev.message_count !== h.message_count || (prev.updated_at || prev.updatedAt) !== (h.updated_at || h.updatedAt)) {
            changed.add(h.id)
          }
        }
        if (changed.size > 0) {
          setHighlightedSessions(changed)
          // 3 秒后自动清除高亮
          setTimeout(() => setHighlightedSessions(new Set()), 3000)
        }
        setHistories(list)
      }
    } catch (_) {
      // ignore; keep current list
    } finally {
      setHistoryLoading(false)
    }
  }

  // 获取指定会话的消息（仅用户提问）
  type Question = { content: string; timestamp?: string }
  type SessionMessages = { [sessionId: string]: Question[] }
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set())
  const [sessionQuestions, setSessionQuestions] = useState<SessionMessages>({})

  async function fetchSessionQuestions(sessionId: string) {
    if (!API_BASE) return
    try {
      const resp = await fetch(`${API_BASE}/history/session/${sessionId}?limit=200&offset=0`)
      if (resp.ok) {
        const data = await resp.json()
        const qs: Question[] = (data?.messages || [])
          .filter((m: any) => m.role === 'user')
          .map((m: any) => ({ content: m.content, timestamp: m.timestamp }))
        setSessionQuestions(prev => ({ ...prev, [sessionId]: qs }))
      }
    } catch (_) {}
  }

  // 删除历史记录
  async function deleteHistory(sessionId: string) {
    if (!API_BASE) return
    try {
      const resp = await fetch(`${API_BASE}/history/session/${sessionId}`, { method: 'DELETE' })
      if (resp.ok) {
        setHistories(prev => prev.filter(h => h.id !== sessionId))
      }
    } catch (_) {}
  }

  useEffect(() => { fetchHistories('') }, [])

  // 初始化读取当前模型
  useEffect(() => {
    async function loadModel() {
      if (!API_BASE) return
      try {
        const resp = await fetch(`${API_BASE}/manage/model/config`)
        if (resp.ok) {
          const data = await resp.json()
          const t = (data?.current_model_type || '').toLowerCase()
          setCurrentModel(t === 'deepseek' ? 'DeepSeek' : 'Ollama')
        }
      } catch (_) {}
    }
    loadModel()
  }, [])

  // 关闭自动轮询历史记录（原每60秒刷新一次）
  // 如果需要重新开启，可恢复为 setInterval 调用

  // 点击外部区域关闭模型选择器
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Element
      if (showModelSelector && !target.closest('.model-selector')) {
        setShowModelSelector(false)
      }
    }

    // ESC键关闭模型选择器
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && showModelSelector) {
        setShowModelSelector(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [showModelSelector])

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

  const [activeTab, setActiveTab] = useState<'chat'|'kb'|'langgraph'>('chat')

  const TopNav = () => (
    <div className="topnav">
      <div className="brand" onClick={() => setActiveTab('chat')}>FastRag</div>
      <div className="nav-center">
        <button className={`nav-btn ${activeTab==='chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
          <span className="icon">💬</span>
          <span>聊天</span>
        </button>
        <button className={`nav-btn ${activeTab==='kb' ? 'active' : ''}`} onClick={() => setActiveTab('kb')}>
          <span className="icon">📚</span>
          <span>知识库</span>
        </button>
      </div>
      <div className="nav-right" />
    </div>
  )

  if (activeTab === 'kb') {
    return (
      <div className={`app full`}> 
        <TopNav />
        <KnowledgeBase 
          onLanggraphTrace={(trace) => {
            setLanggraphTrace(trace)
            // 自动切换到LangGraph页面
            setActiveTab('langgraph')
          }}
          onViewTrace={(filename, trace) => {
            setLanggraphTrace(trace)
            setActiveTab('langgraph')
          }}
          traceStorage={traceStorage}
          setTraceStorage={setTraceStorage}
        />
      </div>
    )
  }

  if (activeTab === 'langgraph') {
    // 处理加载状态
    if (langgraphTrace?.loading) {
      return (
        <div className={`app full`}> 
          <TopNav />
          <div style={{ padding: '20px' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              marginBottom: '20px',
              gap: '12px'
            }}>
              <button 
                onClick={() => setActiveTab('kb')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #dee2e6',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#495057',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e9ecef'
                  e.currentTarget.style.borderColor = '#adb5bd'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f8f9fa'
                  e.currentTarget.style.borderColor = '#dee2e6'
                }}
              >
                <span style={{ fontSize: '16px' }}>←</span>
                <span>返回知识库</span>
              </button>
              <div style={{ 
                height: '20px', 
                width: '1px', 
                backgroundColor: '#dee2e6' 
              }} />
              <h2 style={{ 
                margin: 0, 
                color: '#212529',
                fontSize: '20px',
                fontWeight: '600'
              }}>
                LangGraph Process
              </h2>
            </div>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '50vh',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
              <h3 style={{ margin: '0 0 10px 0', color: '#0369a1' }}>正在处理文件</h3>
              <p style={{ margin: '0', color: '#6b7280' }}>{langgraphTrace.message || '请稍候...'}</p>
            </div>
          </div>
        </div>
      )
    }
    
    // 处理错误状态
    if (langgraphTrace?.error) {
      return (
        <div className={`app full`}> 
          <TopNav />
          <div style={{ padding: '20px' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              marginBottom: '20px',
              gap: '12px'
            }}>
              <button 
                onClick={() => setActiveTab('kb')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #dee2e6',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#495057',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#e9ecef'
                  e.currentTarget.style.borderColor = '#adb5bd'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f8f9fa'
                  e.currentTarget.style.borderColor = '#dee2e6'
                }}
              >
                <span style={{ fontSize: '16px' }}>←</span>
                <span>返回知识库</span>
              </button>
              <div style={{ 
                height: '20px', 
                width: '1px', 
                backgroundColor: '#dee2e6' 
              }} />
              <h2 style={{ 
                margin: 0, 
                color: '#212529',
                fontSize: '20px',
                fontWeight: '600'
              }}>
                LangGraph Process
              </h2>
            </div>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center', 
              height: '50vh',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>❌</div>
              <h3 style={{ margin: '0 0 10px 0', color: '#dc2626' }}>处理失败</h3>
              <p style={{ margin: '0', color: '#6b7280' }}>{langgraphTrace.message || '未知错误'}</p>
              <button 
                style={{
                  marginTop: '20px',
                  padding: '10px 20px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
                onClick={() => setLanggraphTrace(null)}
              >
                返回知识库重新上传
              </button>
            </div>
          </div>
        </div>
      )
    }
    
    // 使用真实的轨迹数据，如果没有则使用演示数据
    const traceData = langgraphTrace || {
      total_steps: 4,
      steps: [
        {
          step: "convert_document",
          status: "success" as const,
          timestamp: new Date().toISOString(),
          duration_ms: 1200,
          input: { filename: "demo.pdf", file_type: "pdf" },
          output: { text_length: 5000, preview: "This is a demo document..." }
        },
        {
          step: "chunk_text",
          status: "success" as const,
          timestamp: new Date().toISOString(),
          duration_ms: 800,
          input: { text_length: 5000 },
          output: { chunk_count: 8, chunk_preview: "This is the first chunk..." }
        },
        {
          step: "generate_embeddings",
          status: "success" as const,
          timestamp: new Date().toISOString(),
          duration_ms: 2000,
          input: { chunk_count: 8 },
          output: { embedding_count: 8, embedding_dim: 1536 }
        },
        {
          step: "store_chunks",
          status: "success" as const,
          timestamp: new Date().toISOString(),
          duration_ms: 500,
          input: { chunk_count: 8 },
          output: { stored_count: 8 }
        }
      ],
      errors: [],
      execution_time: new Date().toISOString()
    };

    return (
      <div className={`app full`}> 
        <TopNav />
        <div style={{ padding: '20px' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            marginBottom: '20px',
            gap: '12px'
          }}>
            <button 
              onClick={() => setActiveTab('kb')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                backgroundColor: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                color: '#495057',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#e9ecef'
                e.currentTarget.style.borderColor = '#adb5bd'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#f8f9fa'
                e.currentTarget.style.borderColor = '#dee2e6'
              }}
            >
              <span style={{ fontSize: '16px' }}>←</span>
              <span>返回知识库</span>
            </button>
            <div style={{ 
              height: '20px', 
              width: '1px', 
              backgroundColor: '#dee2e6' 
            }} />
            <h2 style={{ 
              margin: 0, 
              color: '#212529',
              fontSize: '20px',
              fontWeight: '600'
            }}>
              LangGraph Process
            </h2>
          </div>
          <LangGraphTrace trace={traceData} flowType="document" />
        </div>
      </div>
    )
  }

  return (
    <div className={`app ${sidebarOpen ? 'with-sidebar' : 'sidebar-collapsed'}`}>
      <TopNav />
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
        
        <button className="new-chat" style={{ display: 'none' }} onClick={() => {
          const newId = Math.random().toString(36).slice(2, 8)
          setSessionId(newId)
          setMessages([])
        }}>开启新对话</button>
        <div className="history">
          {historyLoading && <div className="history-loading">加载中...</div>}
          {!historyLoading && histories.map(h => (
            <div key={h.id} className={`history-item-container${expandedSessions.has(h.id) ? ' has-questions' : ''}`}>
              <div className="history-item-row">
                <button
                  className={`history-item ${h.id===sessionId ? 'active': ''} ${highlightedSessions.has(h.id) ? 'highlight' : ''}`}
                  onClick={() => { setSessionId(h.id) }}
                  title={h.updated_at ? new Date(h.updated_at).toLocaleString() : (h.updatedAt ? new Date(h.updatedAt).toLocaleString() : '')}
                >
                  <div className="history-item-content">
                    <div className="history-title">{h.title || h.id}</div>
                    <div className="history-meta">
                      <span
                        className="message-count"
                        onClick={(e) => {
                          e.stopPropagation()
                          setExpandedSessions(prev => {
                            const n = new Set(prev)
                            if (n.has(h.id)) n.delete(h.id); else n.add(h.id)
                            return n
                          })
                          if (!sessionQuestions[h.id]) fetchSessionQuestions(h.id)
                        }}
                      >
                        {h.message_count || 0} 条消息
                      </span>
                      <span className="update-time">
                        {h.updated_at ? new Date(h.updated_at).toLocaleString() : (h.updatedAt ? new Date(h.updatedAt).toLocaleString() : '')}
                      </span>
                    </div>
                  </div>
                </button>
                <button
                  className="history-delete"
                  onClick={(e) => { e.stopPropagation(); if (confirm('确定要删除这个对话吗？')) deleteHistory(h.id) }}
                  title="删除对话"
                >🗑️</button>
              </div>
              {expandedSessions.has(h.id) && (sessionQuestions[h.id]?.length ? (
                <div className="history-questions">
                  {sessionQuestions[h.id].map((q, idx) => (
                    <button key={idx} className="history-question" onClick={() => setQuery(q.content)} title={q.content}>
                      <div className="history-item-content">
                        <div className="history-title">{q.content}</div>
                        {q.timestamp && (
                          <div className="history-meta" style={{ marginTop: 4 }}>
                            <span className="update-time">{new Date(q.timestamp).toLocaleString()}</span>
                          </div>
                        )}
                      </div>
                </button>
                  ))}
                </div>
              ) : expandedSessions.has(h.id) ? (
                <div className="history-questions loading">加载中...</div>
              ) : null)}
              </div>
          ))}
        </div>
      </aside>
      <div className="main">
        <main className="messages" ref={messagesRef}>
        {messages.map((m, i) => {
          if (m.role === 'user') {
            return (
              <div key={i} className={`message user`}>{m.content}</div>
            )
          }
          return (
            <React.Fragment key={i}>
              {m.thought ? (
                <div className="thought">
                  <div className="thought-header">
                    <span className="badge">思考中</span>
                  </div>
                  <div className="thought-body">{m.thought}</div>
                </div>
              ) : null}
              {m.content && (
                <div className="message assistant">
                  <div className="ai-message-header">
                    <div className="ai-logo">
                      <svg width="16" height="16" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2697" xmlnsXlink="http://www.w3.org/1999/xlink">
                        <path d="M454.8 625.6l-63.6-98-4-6.4-1.2-2-2.8-4.4h-10v422h381.6l-3.2-8.8c-3.6-9.2-5.2-18.8-5.2-28.8 0-16.4 4.8-32 14.8-46.8l2-2.8-27.2-66.4 84 24.4 2-0.8c18-6.8 37.2-10 57.2-10 4 0 7.2 0 10 0.4l6.8 0.4v-172H454.8zM882.4 784h-4c-20.8 0-40.8 3.2-59.6 10l-105.6-30.8 34.4 84.8c-10 15.6-15.2 33.2-15.2 51.2 0 8.4 1.2 16.4 3.2 24.4H385.6v-380.4l62 95.6h434.8V784z" fill="#4A555F" p-id="2698"></path>
                        <path d="M375.6 514.4l-3.2 4.4-1.2 2-4.4 6.4-66.4 98H78.8V936h306.8V514.4h-10z m-2.8 408.8H92v-284.8h216l64.8-96.4v381.2z" fill="#4A555F" p-id="2699"></path>
                        <path d="M892.4 514.4H367.2l4 6.4 1.2 2 2.8 4.4 3.2 5.2 6.8 10 62 95.6H972l-79.6-123.6z m-437.6 111.2l-63.6-98h494l62.8 98H454.8z" fill="#4A555F" p-id="2700"></path>
                        <path d="M463.2 610.4l-44-67.6h458l43.6 67.6z" fill="#E0E0E0" p-id="2701"></path>
                        <path d="M79.6 514.4L0 638.4h307.6l64.8-96.4 6.4-9.6 3.6-5.2 3.2-4.4 1.2-2 4.4-6.4H79.6z m221.2 111.2H23.6l62.8-98h280.4l-66 98z" fill="#4A555F" p-id="2702"></path>
                        <path d="M51.6 610.4l43.2-67.6h243.6l-45.6 67.6z" fill="#E0E0E0" p-id="2703"></path>
                        <path d="M486.4 10c-167.2 0-303.6 136-303.6 303.2 0 74.8 26.8 145.6 76 201.2 3.2 3.6 6.8 7.6 10.4 11.2l2 2h430l2-2c3.6-3.6 6.8-7.2 10.4-11.2 49.2-55.6 76-126.4 76-201.2 0.4-167.2-136-303.2-303.2-303.2zM696 514.4H276.8C224.8 460 196 388.8 196 313.6c0-160 130.4-290.4 290.4-290.4 160 0 290.4 130.4 290.4 290.4 0 75.2-28.8 146.4-80.8 200.8z" fill="#4A555F" p-id="2704"></path>
                        <path d="M283.6 499.2c-46.8-50.8-72.4-116.4-72.4-186 0-151.6 123.6-275.2 275.2-275.2s275.2 123.6 275.2 275.2c0 69.2-25.6 135.2-72.4 186H283.6z" fill="#FFD552" p-id="2705"></path>
                        <path d="M486.4 65.6c-136.4 0-247.6 111.2-247.6 247.6 0 79.6 38.8 154.8 103.2 201.2 6 4.4 12 8.4 18.4 12l1.6 0.8h249.6l1.6-0.8c6.4-3.6 12.4-7.6 18.4-12 64-46.4 103.2-121.6 103.2-201.2-0.8-136.4-111.6-247.6-248.4-247.6z m121.2 448.8H365.2C295.2 472 251.6 395.2 251.6 313.6c0-129.6 105.2-234.8 234.8-234.8 129.2 0 234.8 105.2 234.8 234.8 0 81.6-43.6 158.4-113.6 200.8z" fill="#4A555F" p-id="2706"></path>
                        <path d="M482.8 172.4h12.8v38.8h-12.8z" fill="#4A555F" p-id="2707"></path>
                        <path d="M490 297.6h-67.2V204.8h67.2c25.6 0 46.4 20.8 46.4 46.4 0.4 25.6-20.8 46.4-46.4 46.4z m-54.4-12.8h54.4c18.4 0 33.6-15.2 33.6-33.6 0-18.4-15.2-33.6-33.6-33.6h-54.4v67.2z" fill="#4A555F" p-id="2708"></path>
                        <path d="M518.8 395.6h-96V284.8h96c29.2 0 52.8 23.6 52.8 52.8v5.2c0 29.2-23.6 52.8-52.8 52.8z m-83.2-12.8h83.2c22 0 40-18 40-40v-5.2c0-22-18-40-40-40h-83.2v85.2zM440.8 172.4h12.8v38.8h-12.8z" fill="#4A555F" p-id="2709"></path>
                        <path d="M440.8 389.2h12.8v38.8h-12.8zM482.8 389.2h12.8v38.8h-12.8zM878.4 1014c-80.4 0-145.6-51.6-145.6-115.2 0-17.6 5.2-35.2 15.2-51.2l-34.4-84.8 105.6 30.8c18.8-6.8 38.8-10 59.6-10 80.4 0 145.6 51.6 145.6 115.2s-65.6 115.2-146 115.2z m-143.2-230.8l27.2 66-2 2.8c-10 14.4-14.8 30.4-14.8 46.8 0 56.4 59.6 102 132.8 102s132.8-45.6 132.8-102-59.6-102-132.8-102c-20 0-39.2 3.2-57.2 10l-2 0.8-84-24.4z" fill="#4A555F" p-id="2710"></path>
                        <path d="M878.4 986c-64.8 0-117.6-39.2-117.6-86.8 0-13.2 4-26.4 12.4-38.4l6.4-9.6-18.4-44.8 58.4 17.2 6.8-2.4c16.4-6 33.6-9.2 52-9.2 64.8 0 117.6 39.2 117.6 86.8s-52.8 87.2-117.6 87.2z" fill="#FFD552" p-id="2711"></path>
                        <path d="M809.6 865.6h12.8V932h-12.8zM893.6 931.6h-25.2c-12.8 0-22.8-10.4-22.8-22.8v-19.6c0-12.8 10.4-22.8 22.8-22.8h25.2v12.8h-25.2c-5.6 0-10 4.4-10 10v19.6c0 5.6 4.4 10 10 10h25.2v12.8zM932.8 931.6h-3.6c-12.8 0-22.8-10.4-22.8-22.8v-19.6c0-12.8 10.4-22.8 22.8-22.8h3.6v12.8h-3.6c-5.6 0-10 4.4-10 10v19.6c0 5.6 4.4 10 10 10h3.6v12.8z" fill="#4A555F" p-id="2712"></path>
                        <path d="M938 931.6h-8v-12.8h8c5.6 0 10-4.4 10-10v-19.6c0-5.6-4.4-10-10-10h-8v-12.8h8c12.8 0 22.8 10.4 22.8 22.8v19.6c0 12.4-10 22.8-22.8 22.8z" fill="#4A555F" p-id="2713"></path>
                        <path d="M867.2 653.6H439.6l-38.8-59.6v145.6h466.4z" fill="#F68F6F" p-id="2714"></path>
                        <path d="M718 908.4c-0.4-3.2-0.4-6.4-0.4-9.2 0-18 4.8-36 13.6-52.4L687.6 740l131.2 38.4c15.6-5.2 32-8 48.8-9.2v-29.6H400.8v168.8h317.2z" fill="#E0E0E0" p-id="2715"></path>
                        <path d="M357.6 591.6L316 653.6H107.2v86h250.4z" fill="#F68F6F" p-id="2716"></path>
                        <path d="M107.2 739.6h250.4v168.8H107.2z" fill="#E0E0E0" p-id="2717"></path>
                      </svg>
                    </div>
                    <span className="ai-label">AI助手</span>
                  </div>
                  <div className="ai-content">{m.content}</div>
                </div>
              )}
            </React.Fragment>
          )
        })}
        </main>
        <div className="composer">
          {/* 上部分：输入框 */}
          <div className="composer-input">
            <textarea
              rows={1}
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="给 AI 发送消息"
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            />
          </div>
          
          {/* 下部分：操作栏 */}
          <div className="composer-actions">
            <div className="model-selector">
              <button 
                className="model-toggle"
                onClick={() => setShowModelSelector(!showModelSelector)}
              >
                <span className="model-icon">
                  {models.find(m => m.name === currentModel)?.icon || '🤖'}
                </span>
                <span className="model-name">{currentModel}</span>
                <span className="model-arrow">{showModelSelector ? '▲' : '▼'}</span>
              </button>
              {showModelSelector && (
                <div className="model-dropdown">
                  {models.map(model => (
                    <div 
                      key={model.id}
                      className={`model-option ${currentModel === model.name ? 'selected' : ''}`}
                      onClick={() => {
                        setShowModelSelector(false)
                        switchModel(model.id)
                      }}
                    >
                      <div className="model-info">
                        <span className="model-name">{model.name}</span>
                        <span className="model-description">{model.description}</span>
                      </div>
                      {currentModel === model.name && (
                        <span className="checkmark">✓</span>
                      )}
                    </div>
                  ))}
                  <button className="switch-model-btn">
                    切换模型回答
                  </button>
                </div>
              )}
            </div>
            <button className="send" onClick={send} disabled={loading} title="发送">↗</button>
          </div>
        </div>
      </div>
    </div>
  )
}
