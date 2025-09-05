import React, { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

type FileItem = {
  file_name: string
  file_type?: string
  chunk_count?: number
  first_upload?: string
  last_upload?: string
}

type ChunkItem = {
  id: number
  chunk_index: number
  content?: string
  content_preview?: string
}

interface KnowledgeBaseProps {
  onLanggraphTrace?: (trace: any) => void
  onViewTrace?: (filename: string, trace: any) => void
  traceStorage?: Record<string, any>
  setTraceStorage?: (storage: Record<string, any>) => void
}

export default function KnowledgeBase({ onLanggraphTrace, onViewTrace, traceStorage = {}, setTraceStorage }: KnowledgeBaseProps = {}) {
  const [files, setFiles] = useState<FileItem[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all'|'enabled'|'disabled'>('all')
  const [statusMap, setStatusMap] = useState<Record<string, boolean>>({})
  const [traceMap, setTraceMap] = useState<Record<string, boolean>>({})
  const [hoveredMenu, setHoveredMenu] = useState<string | null>(null)
  const [menuTimeout, setMenuTimeout] = useState<NodeJS.Timeout | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<string | null>(null)

  // chunks
  const [chunks, setChunks] = useState<ChunkItem[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [limit, setLimit] = useState(50)
  const [offset, setOffset] = useState(0)
  const [previewLen, setPreviewLen] = useState(200)

  // search in file
  const [searchQ, setSearchQ] = useState('')
  const [searchRes, setSearchRes] = useState<ChunkItem[] | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)

  async function fetchFiles() {
    if (!API_BASE) return
    setLoadingFiles(true)
    try {
      const resp = await fetch(`${API_BASE}/manage/files`)
      if (resp.ok) {
        const data = await resp.json()
        setFiles(Array.isArray(data) ? data : [])
      }
    } finally {
      setLoadingFiles(false)
    }
  }

  async function fetchTraces() {
    if (!API_BASE) return
    try {
      const resp = await fetch(`${API_BASE}/upload/traces`)
      if (resp.ok) {
        const data = await resp.json()
        const traces = data.traces || []
        const traceMap: Record<string, boolean> = {}
        traces.forEach((trace: any) => {
          traceMap[trace.file_name] = true
        })
        setTraceMap(traceMap)
      }
    } catch (error) {
      console.error('获取轨迹数据失败:', error)
    }
  }

  async function getTraceData(fileName: string) {
    if (!API_BASE) return null
    try {
      const resp = await fetch(`${API_BASE}/upload/traces/${encodeURIComponent(fileName)}`)
      if (resp.ok) {
        const data = await resp.json()
        return data.trace
      }
      return null
    } catch (error) {
      console.error('获取轨迹数据失败:', error)
      return null
    }
  }

  async function fetchChunks(fname: string) {
    if (!API_BASE || !fname) return
    setChunksLoading(true)
    try {
      const url = new URL(`${API_BASE}/manage/files/${encodeURIComponent(fname)}/chunks`)
      url.searchParams.set('limit', String(limit))
      url.searchParams.set('offset', String(offset))
      url.searchParams.set('preview_length', String(previewLen))
      const resp = await fetch(url.toString())
      if (resp.ok) {
        const data = await resp.json()
        setChunks(data?.items ?? [])
      }
    } finally {
      setChunksLoading(false)
    }
  }

  async function searchInFile(fname: string, keyword: string) {
    if (!API_BASE || !fname || !keyword) return
    setSearchLoading(true)
    try {
      const url = new URL(`${API_BASE}/manage/files/${encodeURIComponent(fname)}/search`)
      url.searchParams.set('q', keyword)
      url.searchParams.set('limit', '50')
      url.searchParams.set('preview_length', String(previewLen))
      const resp = await fetch(url.toString())
      if (resp.ok) {
        const data = await resp.json()
        setSearchRes(data?.items ?? [])
      }
    } finally {
      setSearchLoading(false)
    }
  }

  const handleDeleteClick = (fname: string) => {
    setFileToDelete(fname)
    setShowDeleteModal(true)
  }

  const confirmDelete = async () => {
    if (!API_BASE || !fileToDelete) return
    const resp = await fetch(`${API_BASE}/manage/files/${encodeURIComponent(fileToDelete)}`, { method: 'DELETE' })
    if (resp.ok) {
      if (selectedFile === fileToDelete) {
        setSelectedFile(null)
        setChunks([])
        setSearchRes(null)
      }
      // 刷新文件列表和轨迹数据
      fetchFiles()
      fetchTraces()
    }
    setShowDeleteModal(false)
    setFileToDelete(null)
  }

  const cancelDelete = () => {
    setShowDeleteModal(false)
    setFileToDelete(null)
  }

  // 处理菜单悬浮事件
  const handleMenuMouseEnter = (fileName: string) => {
    if (menuTimeout) {
      clearTimeout(menuTimeout)
      setMenuTimeout(null)
    }
    setHoveredMenu(fileName)
  }

  const handleMenuMouseLeave = () => {
    const timeout = setTimeout(() => {
      setHoveredMenu(null)
    }, 300) // 300ms延迟隐藏
    setMenuTimeout(timeout)
  }

  // upload simple
  async function uploadSimple(files: FileList | null) {
    if (!API_BASE || !files || files.length === 0) return
    const form = new FormData()
    Array.from(files).forEach(f => form.append('files', f))
    const resp = await fetch(`${API_BASE}/upload/simple`, { method: 'POST', body: form })
    if (resp.ok) fetchFiles()
  }

  // upload docling
  async function uploadDocling(files: FileList | null) {
    if (!API_BASE || !files || files.length === 0) return
    const form = new FormData()
    Array.from(files).forEach(f => form.append('files', f))
    const resp = await fetch(`${API_BASE}/upload/docling`, { method: 'POST', body: form })
    if (resp.ok) fetchFiles()
  }

  // upload with LangGraph
  async function uploadLangGraph(files: FileList | null) {
    if (!API_BASE || !files || files.length === 0) return
    
    console.log('开始LangGraph上传，文件数量:', files.length)
    
    // 立即跳转到LangGraph页面，显示加载状态
    if (onLanggraphTrace) {
      onLanggraphTrace({ loading: true, message: '正在处理文件，请稍候...' })
    }
    
    const form = new FormData()
    Array.from(files).forEach(f => form.append('files', f))
    
    try {
      console.log('发送请求到:', `${API_BASE}/upload/langgraph`)
      const resp = await fetch(`${API_BASE}/upload/langgraph`, { method: 'POST', body: form })
      console.log('响应状态:', resp.status)
      
      if (resp.ok) {
        const data = await resp.json()
        console.log('响应数据:', data)
        fetchFiles()
        
        // 将轨迹数据传递给父组件
        if (onLanggraphTrace && data.results && data.results.length > 0) {
          // 保存所有文件的轨迹数据
          data.results.forEach((result: any) => {
            if (result.execution_trace && result.filename) {
              setTraceStorage?.((prev: Record<string, any>) => ({
                ...prev,
                [result.filename]: result.execution_trace
              }))
            }
          })
          
          // 使用第一个文件的轨迹数据
          const firstResult = data.results[0]
          if (firstResult.execution_trace) {
            onLanggraphTrace(firstResult.execution_trace)
          }
        }
      } else {
        const errorText = await resp.text()
        console.error('上传失败:', errorText)
        // 更新LangGraph页面显示错误
        if (onLanggraphTrace) {
          onLanggraphTrace({ error: true, message: `上传失败: ${errorText}` })
        }
      }
    } catch (error) {
      console.error('上传错误:', error)
      // 更新LangGraph页面显示错误
      if (onLanggraphTrace) {
        onLanggraphTrace({ error: true, message: `上传错误: ${error}` })
      }
    }
  }

  useEffect(() => { 
    fetchFiles()
    fetchTraces()
  }, [])
  useEffect(() => {
    const t = setInterval(() => {
      fetchFiles()
      fetchTraces()
    }, 30_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => { if (selectedFile) fetchChunks(selectedFile) }, [selectedFile, limit, offset, previewLen])

  const filteredFiles = files
    .filter(f => !q || f.file_name.toLowerCase().includes(q.toLowerCase()))
    .filter(f => {
      const enabled = statusMap[f.file_name] ?? true
      if (statusFilter === 'all') return true
      if (statusFilter === 'enabled') return enabled
      return !enabled
    })

  const ListView = (
    <div className="kb">
      
      <div className="kb-toolbar">
        <div className="kb-uploaders">
          <label className="uploader">上传（简单文本）
            <input type="file" multiple onChange={e => uploadSimple(e.target.files)} />
          </label>
          <label className="uploader">上传（Docling 解析）
            <input type="file" multiple onChange={e => uploadDocling(e.target.files)} />
          </label>
          <label className="uploader">上传（LangGraph 轨迹）
            <input type="file" multiple onChange={e => uploadLangGraph(e.target.files)} />
          </label>
        </div>
        <div className="kb-search">
          <div className="filter">
            <button className="select" onClick={(e)=>{
              const el = (e.currentTarget.nextSibling as HTMLElement)
              if (el) el.classList.toggle('open')
            }}>{statusFilter==='all'?'All Status':statusFilter==='enabled'?'可用':'停用'}</button>
            <div className="select-menu" onMouseLeave={(e)=>{(e.currentTarget as HTMLElement).classList.remove('open')}}>
              <div className="option" onClick={()=>setStatusFilter('all')}>All Status</div>
              <div className="option" onClick={()=>setStatusFilter('enabled')}>可用</div>
              <div className="option" onClick={()=>setStatusFilter('disabled')}>停用</div>
            </div>
          </div>
          <input placeholder="搜索文件名..." value={q} onChange={e => setQ(e.target.value)} />
          <button onClick={fetchFiles}>刷新</button>
        </div>
      </div>

      <div className="kb-table">
        <div className="kb-table-header" style={{ 
          display: 'flex', 
          width: '100%',
          whiteSpace: 'nowrap'
        }}>
          <div className="col idx" style={{ width: '60px', flex: '0 0 60px', padding: '12px 8px' }}>#</div>
          <div className="col name" style={{ width: '300px', flex: '1 1 300px', padding: '12px 8px' }}>名称</div>
          <div className="col mode" style={{ width: '120px', flex: '0 0 120px', padding: '12px 8px' }}>分段模式</div>
          <div className="col chars" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>字符数</div>
          <div className="col recall" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>召回次数</div>
          <div className="col time" style={{ width: '180px', flex: '0 0 180px', padding: '12px 8px' }}>上传时间</div>
          <div className="col status" style={{ width: '80px', flex: '0 0 80px', padding: '12px 8px' }}>状态</div>
          <div className="col langgraph" style={{ width: '140px', flex: '0 0 140px', padding: '12px 8px' }}>LangGraph</div>
          <div className="col actions" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>操作</div>
        </div>
        {loadingFiles && <div className="loading">加载文件列表...</div>}
        {!loadingFiles && filteredFiles.map((f, i) => (
          <div key={f.file_name} className={`kb-table-row`} style={{ 
            display: 'flex', 
            width: '100%',
            whiteSpace: 'nowrap'
          }}>
            <div className="col idx" style={{ width: '60px', flex: '0 0 60px', padding: '12px 8px' }}>{i+1}</div>
            <div 
              className="col name link" 
              title={f.file_name} 
              onClick={()=>setSelectedFile(f.file_name)}
              style={{
                width: '300px',
                flex: '1 1 300px',
                padding: '12px 8px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}
            >
              {f.file_name}
            </div>
            <div className="col mode" style={{ width: '120px', flex: '0 0 120px', padding: '12px 8px' }}><span className="badge">通用</span></div>
            <div className="col chars" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>-</div>
            <div className="col recall" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>0</div>
            <div className="col time" style={{ 
              width: '180px', 
              flex: '0 0 180px',
              padding: '12px 8px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {f.last_upload ? new Date(f.last_upload).toLocaleString() : ''}
            </div>
            <div className="col status" style={{ width: '80px', flex: '0 0 80px', padding: '12px 8px' }}>
              <label className="switch">
                <input type="checkbox" checked={(statusMap[f.file_name] ?? true)} onChange={(e)=>{
                  const on = (e.target as HTMLInputElement).checked
                  setStatusMap(prev => ({...prev, [f.file_name]: on}))
                }} />
                <span className="slider" />
              </label>
            </div>
            <div className="col langgraph" style={{ width: '140px', flex: '0 0 140px', padding: '12px 8px' }}>
              {traceMap[f.file_name] ? (
                <button 
                  className="langgraph-btn"
                  onClick={async () => {
                    // 从数据库获取真实轨迹数据
                    const traceData = await getTraceData(f.file_name);
                    if (traceData && onViewTrace) {
                      onViewTrace(f.file_name, traceData);
                    }
                  }}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  查看流程
                </button>
              ) : (
                <button 
                  className="langgraph-btn"
                  onClick={async () => {
                    // 先尝试从数据库获取真实轨迹数据
                    const traceData = await getTraceData(f.file_name);
                    if (traceData && onViewTrace) {
                      // 如果找到真实数据，使用真实数据
                      onViewTrace(f.file_name, traceData);
                      // 更新轨迹映射，避免下次显示错误状态
                      setTraceMap(prev => ({ ...prev, [f.file_name]: true }));
                    } else {
                      // 如果没有找到真实数据，使用模拟数据
                      const mockTrace = {
                        total_steps: 4,
                        steps: [
                          {
                            step: "convert_document",
                            status: "success" as const,
                            timestamp: new Date().toISOString(),
                            duration_ms: 1200,
                            input: { filename: f.file_name, file_type: f.file_type || "unknown" },
                            output: { text_length: 5000, preview: `这是文件 ${f.file_name} 的文档转换结果...` }
                          },
                          {
                            step: "chunk_text",
                            status: "success" as const,
                            timestamp: new Date().toISOString(),
                            duration_ms: 800,
                            input: { text_length: 5000 },
                            output: { chunk_count: 8, chunks: [`分块1: 这是文件 ${f.file_name} 的第一个分块内容...`, `分块2: 这是文件 ${f.file_name} 的第二个分块内容...`] }
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
                      
                      // 跳转到LangGraph页面
                      if (onViewTrace) {
                        onViewTrace(f.file_name, mockTrace);
                      }
                    }
                  }}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#6b7280',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  查看流程
                </button>
              )}
            </div>
            <div className="col actions" style={{ width: '100px', flex: '0 0 100px', padding: '12px 8px' }}>
              <div 
                className="more"
                onMouseEnter={() => handleMenuMouseEnter(f.file_name)}
                onMouseLeave={handleMenuMouseLeave}
              >
                <button className="icon">⋯</button>
                <div className={`menu ${hoveredMenu === f.file_name ? 'show' : ''}`}>
                  <div className="item" onClick={()=>setSelectedFile(f.file_name)}>查看</div>
                  <div className="item danger" onClick={()=>handleDeleteClick(f.file_name)}>删除</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 删除确认弹窗 */}
      {showDeleteModal && (
        <div className="delete-modal-overlay" onClick={cancelDelete}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <h3>确定删除 {fileToDelete} 吗?</h3>
            <p>这将删除文件的所有数据，包括向量数据和轨迹数据。删除后无法恢复。</p>
            <div className="delete-modal-actions">
              <button className="cancel-btn" onClick={cancelDelete}>取消</button>
              <button className="confirm-btn" onClick={confirmDelete}>我确定</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const DetailView = selectedFile ? (
    <div className="kb">
      <div className="kb-toolbar">
        <div style={{display:'flex', alignItems:'center', gap:8}}>
          <button onClick={()=>{ setSelectedFile(null); setSearchRes(null); }}>← 返回</button>
          <span className="title">{selectedFile}</span>
        </div>
        <div className="kb-search">
          <label>预览长度
            <input type="number" min={50} max={1000} value={previewLen} onChange={e => setPreviewLen(parseInt(e.target.value||'200'))} />
          </label>
          <label>每页
            <input type="number" min={10} max={200} value={limit} onChange={e => setLimit(parseInt(e.target.value||'50'))} />
          </label>
          <button onClick={() => { setOffset(Math.max(0, offset - limit)) }}>上一页</button>
          <button onClick={() => { setOffset(offset + limit) }}>下一页</button>
          <input placeholder="在当前文件内检索关键词..." value={searchQ} onChange={e => setSearchQ(e.target.value)} />
          <button onClick={() => searchInFile(selectedFile, searchQ)} disabled={!searchQ}>检索</button>
          {searchRes && <button onClick={() => setSearchRes(null)}>清除检索</button>}
        </div>
      </div>

      <div className="kb-detail-only">
        {chunksLoading && <div className="loading">加载分段...</div>}
        {!chunksLoading && !searchRes && (
          <div className="kb-chunks">
            {chunks.map(c => (
              <div key={c.id} className="kb-chunk">
                <div className="kb-chunk-meta">#{c.chunk_index}</div>
                <div className="kb-chunk-content">{c.content_preview ?? c.content}</div>
              </div>
            ))}
          </div>
        )}
        {searchRes && (
          <div className="kb-chunks">
            {searchLoading && <div className="loading">检索中...</div>}
            {!searchLoading && searchRes.map((c, i) => (
              <div key={`${c.id}-${i}`} className="kb-chunk search">
                <div className="kb-chunk-meta">#{c.chunk_index}</div>
                <div className="kb-chunk-content">{c.content_preview ?? c.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  ) : null

  return (
    <>
      {selectedFile ? DetailView : ListView}
    </>
  )
}


