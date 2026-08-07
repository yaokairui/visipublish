import { useSyncExternalStore } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

type Kind = 'success' | 'error' | 'warn' | 'info'
export interface ToastMsg {
  id: number
  kind: Kind
  text: string
}
export interface ToastApi {
  success(text: string): void
  error(text: string): void
  warn(text: string): void
  info(text: string): void
}

let toasts: ToastMsg[] = []
let seq = 0
const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((l) => l())
}

function push(kind: Kind, text: string) {
  const id = ++seq
  toasts = [...toasts, { id, kind, text }]
  emit()
  window.setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    emit()
  }, 4000)
}

export function useToast(): ToastApi {
  return {
    success: (t) => push('success', t),
    error: (t) => push('error', t),
    warn: (t) => push('warn', t),
    info: (t) => push('info', t),
  }
}

const ICONS: Record<Kind, React.ReactNode> = {
  success: <CheckCircle2 size={16} className="text-accent shrink-0" />,
  error: <XCircle size={16} className="text-danger shrink-0" />,
  warn: <AlertTriangle size={16} className="text-warning shrink-0" />,
  info: <Info size={16} className="text-sky-400 shrink-0" />,
}

export function Toasts() {
  const list = useSyncExternalStore(
    (cb) => {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    () => toasts,
  )
  return (
    <div className="fixed right-4 top-4 z-50 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2">
      {list.map((t) => (
        <div
          key={t.id}
          className="card flex items-start gap-2.5 px-4 py-3 text-sm shadow-lg shadow-black/40"
          role="status"
        >
          {ICONS[t.kind]}
          <span className="break-all">{t.text}</span>
        </div>
      ))}
    </div>
  )
}
