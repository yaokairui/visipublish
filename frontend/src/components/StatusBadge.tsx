import type { ReactNode } from 'react'

const STYLES: Record<string, string> = {
  pending: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  publishing: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  success: 'bg-green-500/15 text-green-300 border-green-500/40',
  failed: 'bg-red-500/15 text-red-300 border-red-500/40',
  skipped: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  delisted: 'bg-slate-600/15 text-slate-400 border-slate-500/40',
}

const LABELS: Record<string, string> = {
  pending: '待发布',
  publishing: '发布中',
  success: '已上架',
  failed: '失败',
  skipped: '已跳过',
  delisted: '已下架',
}

export function StatusBadge({ status }: { status: string }) {
  const base = STYLES[status] || STYLES.pending
  const pulsing = status === 'publishing'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${base} ${
        pulsing ? 'animate-pulse' : ''
      }`}
    >
      {pulsing && <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />}
      {LABELS[status] || status}
    </span>
  )
}

export function SourceBadge({ source }: { source?: string }) {
  const isApi = source === 'api'
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${
        isApi
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-300'
          : 'border-slate-500/40 bg-slate-500/10 text-slate-400'
      }`}
    >
      {isApi ? '真实 Vision API' : '内置 Mock'}
    </span>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}
