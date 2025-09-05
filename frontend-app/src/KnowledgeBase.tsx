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

export default function KnowledgeBase() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all'|'enabled'|'disabled'>('all')
  const [statusMap, setStatusMap] = useState<Record<string, boolean>>({})

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

  async function deleteFile(fname: string) {
    if (!API_BASE || !fname) return
    if (!confirm(`确定删除 ${fname} 吗？`)) return
    const resp = await fetch(`${API_BASE}/manage/files/${encodeURIComponent(fname)}`, { method: 'DELETE' })
    if (resp.ok) {
      if (selectedFile === fname) {
        setSelectedFile(null)
        setChunks([])
        setSearchRes(null)
      }
      fetchFiles()
    }
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

  useEffect(() => { fetchFiles() }, [])
  useEffect(() => {
    const t = setInterval(() => fetchFiles(), 30_000)
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
        <div className="kb-table-header">
          <div className="col idx">#</div>
          <div className="col name">名称</div>
          <div className="col mode">分段模式</div>
          <div className="col chars">字符数</div>
          <div className="col recall">召回次数</div>
          <div className="col time">上传时间</div>
          <div className="col status">状态</div>
          <div className="col actions">操作</div>
        </div>
        {loadingFiles && <div className="loading">加载文件列表...</div>}
        {!loadingFiles && filteredFiles.map((f, i) => (
          <div key={f.file_name} className={`kb-table-row`}>
            <div className="col idx">{i+1}</div>
            <div className="col name link" title={f.file_name} onClick={()=>setSelectedFile(f.file_name)}>{f.file_name}</div>
            <div className="col mode"><span className="badge">通用</span></div>
            <div className="col chars">-</div>
            <div className="col recall">0</div>
            <div className="col time">{f.last_upload ? new Date(f.last_upload).toLocaleString() : ''}</div>
            <div className="col status">
              <label className="switch">
                <input type="checkbox" checked={(statusMap[f.file_name] ?? true)} onChange={(e)=>{
                  const on = (e.target as HTMLInputElement).checked
                  setStatusMap(prev => ({...prev, [f.file_name]: on}))
                }} />
                <span className="slider" />
              </label>
            </div>
            <div className="col actions">
              <div className="more">
                <button className="icon">⋯</button>
                <div className="menu">
                  <div className="item" onClick={()=>setSelectedFile(f.file_name)}>查看</div>
                  <div className="item danger" onClick={()=>deleteFile(f.file_name)}>删除</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
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

  return selectedFile ? DetailView : ListView
}


