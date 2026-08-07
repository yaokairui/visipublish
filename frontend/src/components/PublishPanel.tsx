import { CheckCircle2, Loader2, Rocket, XCircle } from 'lucide-react'
import type { Item, PublishStatus } from '../types'

interface PublishPanelProps {
  items: Item[]
  selectedIds: Set<string>
  job: PublishStatus | null
  polling: boolean
  onPublish: (ids: string[]) => void
}

export default function PublishPanel({
  items,
  selectedIds,
  job,
  polling,
  onPublish,
}: PublishPanelProps) {
  const selected = items.filter((it) => selectedIds.has(it.id))
  const pending = selected.filter((it) => it.status !== 'success' && it.status !== 'delisted')
  const running = polling || job?.running
  const done = job && !job.running

  return (
    <section className="card mt-6 p-5">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 font-mono text-xs text-accent">
          3
        </span>
        批量上架
        <Rocket size={17} className="text-muted" />
      </h2>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          待上架{' '}
          <span className="font-mono text-foreground">{pending.length}</span> 条（已勾选{' '}
          <span className="font-mono text-foreground">{selected.length}</span> 条）
        </p>
        <button
          className="btn btn-primary px-6"
          disabled={running || pending.length === 0}
          onClick={() => onPublish(pending.map((it) => it.id))}
        >
          {running ? <Loader2 size={15} className="animate-spin" /> : <Rocket size={15} />}
          {running ? '正在上架…' : '确认无误，批量上架'}
        </button>
      </div>

      {job && (
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between text-xs text-muted">
            <span>
              进度：{job.success + job.failed} / {job.total}
            </span>
            <span>
              成功 <span className="font-mono text-green-400">{job.success}</span> · 失败{' '}
              <span className="font-mono text-red-400">{job.failed}</span>
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-accent transition-all duration-300"
              style={{
                width: job.total ? `${((job.success + job.failed) / job.total) * 100}%` : '0%',
              }}
            />
          </div>
          {job.error && (
            <p className="mt-2 text-xs text-red-300">任务异常：{job.error}</p>
          )}
        </div>
      )}

      {done && (
        <div className="mt-4 space-y-1.5">
          {job.items.map((r) => (
            <div
              key={r.id}
              className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm"
            >
              {r.status === 'success' ? (
                <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-green-400" />
              ) : (
                <XCircle size={15} className="mt-0.5 shrink-0 text-red-400" />
              )}
              <div className="min-w-0">
                <div className="truncate">{r.title || r.message}</div>
                {r.message && r.message !== r.title && (
                  <div className="text-xs text-muted">{r.message}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
