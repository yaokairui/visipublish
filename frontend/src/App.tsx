import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, PackageOpen } from 'lucide-react'
import { api, setSession } from './api'
import type { Config, Item, PublishStatus, ReviewPatch } from './types'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import ReviewTable from './components/ReviewTable'
import PublishPanel from './components/PublishPanel'
import { Toasts, useToast } from './components/Toast'

export default function App() {
  const [config, setConfig] = useState<Config | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [generating, setGenerating] = useState(false)
  const [job, setJob] = useState<PublishStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const jobRef = useRef<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    ;(async () => {
      try {
        const { session_id } = await api.createSession()
        setSession(session_id)
        setConfig(await api.config())
      } catch (e) {
        toast.error(`初始化失败：${(e as Error).message}`)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const replaceItems = useCallback((next: Item[]) => {
    setItems(next)
    setSelectedIds((prev) => new Set([...prev].filter((id) => next.some((it) => it.id === id))))
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!files.length) {
      toast.warn('请先选择商品图片')
      return
    }
    setGenerating(true)
    try {
      const res = await api.generate(files)
      replaceItems(res.items)
      setSelectedIds(
        new Set(res.items.filter((it) => it.status !== 'skipped').map((it) => it.id)),
      )
      setFiles([])
      toast.success(`已生成 ${res.items.length} 条商品记录`)
    } catch (e) {
      toast.error(`生成失败：${(e as Error).message}`)
    } finally {
      setGenerating(false)
    }
  }, [files, replaceItems, toast])

  const handleReview = useCallback(
    async (id: string, patch: ReviewPatch) => {
      try {
        const { item } = await api.review(id, patch)
        setItems((prev) => prev.map((it) => (it.id === item.id ? item : it)))
      } catch (e) {
        toast.error(`保存失败：${(e as Error).message}`)
      }
    },
    [toast],
  )

  const handleRegen = useCallback(
    async (id: string) => {
      try {
        const { item } = await api.regen(id)
        setItems((prev) => prev.map((it) => (it.id === item.id ? item : it)))
        toast.success('已重新生成该条商品')
      } catch (e) {
        toast.error(`重新生成失败：${(e as Error).message}`)
      }
    },
    [toast],
  )

  const handleDelist = useCallback(
    async (id: string) => {
      try {
        const res = await api.delist(id)
        if (res.ok) {
          setItems((prev) => prev.map((it) => (it.id === id ? { ...it, status: 'delisted' } : it)))
          toast.success(res.message)
        } else {
          toast.error(res.message)
        }
      } catch (e) {
        toast.error(`下架失败：${(e as Error).message}`)
      }
    },
    [toast],
  )

  // 发布任务轮询
  useEffect(() => {
    if (!polling) return
    let stopped = false
    const timer = window.setInterval(async () => {
      const jid = jobRef.current
      if (!jid) {
        window.clearInterval(timer)
        return
      }
      try {
        const st = await api.publishStatus(jid)
        if (stopped) return
        setJob(st)
        if (!st.running) {
          window.clearInterval(timer)
          jobRef.current = null
          setPolling(false)
          const { items: fresh } = await api.listItems()
          replaceItems(fresh)
          if (st.failed > 0) toast.warn(`上架完成：成功 ${st.success} / 失败 ${st.failed}`)
          else toast.success(`批量上架成功 ${st.success} 条`)
        }
      } catch (e) {
        window.clearInterval(timer)
        jobRef.current = null
        setPolling(false)
        toast.error(`查询任务失败：${(e as Error).message}`)
      }
    }, 1000)
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [polling, replaceItems, toast])

  const handlePublish = useCallback(
    async (ids: string[]) => {
      try {
        const { job_id } = await api.publish(ids)
        jobRef.current = job_id
        setJob({ running: true, total: ids.length, success: 0, failed: 0, items: [], error: '' })
        setPolling(true)
      } catch (e) {
        toast.error(`发布失败：${(e as Error).message}`)
      }
    },
    [toast],
  )

  const handleClearSession = useCallback(async () => {
    try {
      await api.clearSession()
    } catch {
      /* ignore */
    }
    setItems([])
    setFiles([])
    setSelectedIds(new Set())
    setJob(null)
    jobRef.current = null
    setPolling(false)
    const { session_id } = await api.createSession()
    setSession(session_id)
    setConfig(await api.config())
    toast.success('会话已重置')
  }, [toast])

  const toggleSelected = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleAll = useCallback((ids: string[]) => {
    setSelectedIds((prev) => {
      const allSelected = ids.length > 0 && ids.every((id) => prev.has(id))
      const next = new Set(prev)
      ids.forEach((id) => {
        if (allSelected) next.delete(id)
        else next.add(id)
      })
      return next
    })
  }, [])

  if (!config) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={28} />
        <span className="ml-3 text-muted">正在初始化服务…</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <Sidebar config={config} itemCount={items.length} onClear={handleClearSession} />
      <main className="mx-auto max-w-6xl px-6 py-6 lg:ml-72">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">电商 AI 智能上架助手</h1>
          <p className="mt-1 text-sm text-muted">
            批量识别商品图 → AI / 规则生成标题 → 人工审核 → 渠道自动上架（模拟后台）
          </p>
        </header>

        <UploadZone
          files={files}
          setFiles={setFiles}
          batchLimit={config.batch_limit}
          generating={generating}
          onGenerate={handleGenerate}
        />

        {items.length > 0 && (
          <ReviewTable
            items={items}
            config={config}
            selectedIds={selectedIds}
            onToggle={toggleSelected}
            onToggleAll={toggleAll}
            onReview={handleReview}
            onRegen={handleRegen}
            onDelist={handleDelist}
          />
        )}

        {items.length > 0 && (
          <PublishPanel
            items={items}
            selectedIds={selectedIds}
            job={job}
            polling={polling}
            onPublish={handlePublish}
          />
        )}

        {items.length === 0 && !generating && (
          <div className="card mt-6 flex flex-col items-center gap-3 py-16 text-muted">
            <PackageOpen size={40} className="opacity-60" />
            <p className="text-sm">上传图片并点击「开始生成」，识别结果会出现在这里</p>
          </div>
        )}
      </main>
      <Toasts />
    </div>
  )
}
