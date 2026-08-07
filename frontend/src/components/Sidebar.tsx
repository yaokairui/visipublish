import { Bot, Boxes, Eye, RefreshCcw, Server, Trash2 } from 'lucide-react'
import type { Config } from '../types'

interface SidebarProps {
  config: Config
  itemCount: number
  onClear: () => void
}

export default function Sidebar({ config, itemCount, onClear }: SidebarProps) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col border-r border-border bg-surface lg:flex">
      <div className="border-b border-border px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <Bot size={20} />
          </div>
          <div>
            <div className="font-mono text-sm font-semibold tracking-tight">VisiPublish</div>
            <div className="text-[11px] text-muted">AI 智能上架助手</div>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
        <section>
          <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
            系统状态
          </h2>
          <div className="space-y-2.5 text-sm">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted">
                <Bot size={14} /> 识别模式
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                  config.vision_configured
                    ? 'border-green-500/40 bg-green-500/10 text-green-300'
                    : 'border-slate-500/40 bg-slate-500/10 text-slate-400'
                }`}
              >
                {config.vision_configured ? '真实 Vision API' : '内置 Mock'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted">
                <Server size={14} /> 发布渠道
              </span>
              <span className="font-mono text-xs">{config.channel}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted">
                <Eye size={14} /> RPA 模式
              </span>
              <span className="font-mono text-xs">{config.rpa_headless ? '无头' : '可见浏览器'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted">
                <Boxes size={14} /> 批量上限
              </span>
              <span className="font-mono text-xs">{config.batch_limit} 张</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">模型</span>
              <span className="max-w-[10rem] truncate font-mono text-xs">{config.vision_model}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">模拟后台</span>
              <span className="font-mono text-xs">{config.mock_backend_url}</span>
            </div>
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
            当前会话
          </h2>
          <div className="text-sm text-muted">
            商品记录 <span className="font-mono text-foreground">{itemCount}</span> 条
          </div>
        </section>
      </div>

      <div className="space-y-3 border-t border-border px-5 py-4">
        <button className="btn w-full" onClick={onClear}>
          <Trash2 size={15} />
          清除会话
        </button>
        <button className="btn w-full" onClick={() => window.location.reload()}>
          <RefreshCcw size={15} />
          刷新页面
        </button>
        <p className="text-center text-[11px] text-muted/70">
          Streamlit 已弃用 · React + FastAPI
        </p>
      </div>
    </aside>
  )
}
