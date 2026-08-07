import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Loader2, RefreshCw, Terminal, Trash2 } from 'lucide-react'
import type { Config, Item, ReviewPatch } from '../types'
import { Field, SourceBadge, StatusBadge } from './StatusBadge'

interface ItemRowProps {
  item: Item
  index: number
  config: Config
  selected: boolean
  onToggle: () => void
  onReview: (id: string, patch: ReviewPatch) => void
  onRegen: (id: string) => void
  onDelist: (id: string) => void
}

interface Draft {
  title_source: string
  manual_title: string
  category: string
  attributes: Record<string, string>
  prompts: string[]
}

export default function ItemRow({
  item,
  index,
  config,
  selected,
  onToggle,
  onReview,
  onRegen,
  onDelist,
}: ItemRowProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState<Draft>({
    title_source: item.title_source,
    manual_title: item.manual_title,
    category: item.category,
    attributes: item.attributes,
    prompts: item.prompts,
  })
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  // 后端 review 回写后同步服务端解析结果（含类目切换后的默认属性）
  useEffect(() => {
    setDraft((d) => ({ ...d, attributes: item.attributes }))
  }, [item.attributes])

  const push = (next: Draft) => {
    setDraft(next)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => onReview(item.id, { ...next, selected: true }), 600)
  }
  const set = (patch: Partial<Draft>) => push({ ...draft, ...patch })

  const rule = config.category_rules.find((r) => r.name === draft.category)
  const titleOptions: { value: string; label: string }[] = [
    ...item.ai_titles.map((t, i) => ({
      value: `ai-${i + 1}`,
      label: `AI 标题 ${i + 1}：${t}`,
    })),
    { value: 'rule', label: `规则模板：${item.rule_title}` },
    { value: 'manual', label: '手动输入' },
  ]
  const isSkipped = item.status === 'skipped'

  const handleRegen = async () => {
    setBusy(true)
    try {
      await onRegen(item.id)
    } finally {
      setBusy(false)
    }
  }

  const handleDelist = async () => {
    setBusy(true)
    try {
      await onDelist(item.id)
    } finally {
      setBusy(false)
    }
  }

  const screenshotUrl = item.rpa_result?.screenshot
    ? `/api/rpa_screenshot/${item.rpa_result.screenshot.split(/[\\/]/).pop()}`
    : null

  return (
    <div className="card overflow-hidden">
      <div
        className="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-2/60"
        onClick={() => setOpen((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen((v) => !v)
          }
        }}
        aria-expanded={open}
      >
        <input
          type="checkbox"
          className="h-3.5 w-3.5 shrink-0 cursor-pointer accent-green-500"
          checked={selected}
          disabled={isSkipped}
          aria-label={`勾选 ${item.name}`}
          onChange={(e) => {
            e.stopPropagation()
            onToggle()
          }}
          onClick={(e) => e.stopPropagation()}
        />
        <span className="font-mono text-xs text-muted">{String(index + 1).padStart(2, '0')}</span>
        <span className="flex-1 truncate text-sm font-medium">{item.name}</span>
        <SourceBadge source={item.vision?.source} />
        <StatusBadge status={item.status} />
        <ChevronDown
          size={16}
          className={`text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </div>

      {open && (
        <div className="grid gap-6 border-t border-border px-5 py-5 lg:grid-cols-[240px_1fr]">
          {/* 左：原图 + 占位图 */}
          <div className="space-y-3">
            {item.vision && (
              <div className="rounded-lg border border-border bg-surface-2 p-3">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  识别结果
                </div>
                <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-slate-300">
                  {JSON.stringify(item.vision, null, 2)}
                </pre>
              </div>
            )}
            {item.placeholders.length > 0 && (
              <div>
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  AI 生图占位图（Pillow）
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {item.placeholders.map((p, i) => (
                    <img
                      key={p}
                      src={p}
                      alt={`占位图 ${i + 1}`}
                      loading="lazy"
                      className="aspect-square w-full rounded-md border border-border object-cover"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 右：编辑区 */}
          {isSkipped ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">
              该图片生成失败：{item.error}
            </div>
          ) : (
            <div className="space-y-5">
              <Field label="标题来源">
                <select
                  className="input"
                  value={draft.title_source}
                  onChange={(e) => set({ title_source: e.target.value })}
                >
                  {titleOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                {draft.title_source === 'manual' ? (
                  <input
                    className="input mt-2"
                    placeholder="输入你的商品标题"
                    value={draft.manual_title}
                    onChange={(e) => set({ manual_title: e.target.value })}
                  />
                ) : (
                  <div className="mt-2 rounded-md border border-accent/20 bg-accent/5 px-3 py-2 font-mono text-xs text-green-200">
                    {item.title || '（等待解析）'}
                  </div>
                )}
                {item.ai_titles.length === 0 && (
                  <p className="mt-1.5 text-[11px] text-warning">
                    AI 标题不可用（未配置 API Key 或生成失败），已回退规则模板
                  </p>
                )}
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="商品类目">
                  <select
                    className="input"
                    value={draft.category}
                    onChange={(e) => set({ category: e.target.value })}
                  >
                    {config.categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  {rule &&
                    Object.entries(rule.attribute_spec).map(([key, spec]) => (
                      <Field key={key} label={config.attribute_labels[key] || key}>
                        {spec.type === 'choice' ? (
                          <select
                            className="input"
                            value={draft.attributes[key] || ''}
                            onChange={(e) =>
                              set({ attributes: { ...draft.attributes, [key]: e.target.value } })
                            }
                          >
                            {(spec.options || []).map((o) => (
                              <option key={o} value={o}>
                                {o}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            className="input"
                            value={draft.attributes[key] || ''}
                            onChange={(e) =>
                              set({ attributes: { ...draft.attributes, [key]: e.target.value } })
                            }
                          />
                        )}
                      </Field>
                    ))}
                </div>
              </div>

              <div>
                <label className="label">AI 生图提示词 × 3（可修改）</label>
                <div className="grid gap-3 md:grid-cols-3">
                  {[0, 1, 2].map((i) => (
                    <textarea
                      key={i}
                      className="input min-h-24 resize-y font-mono text-[11px]"
                      value={draft.prompts[i] || ''}
                      onChange={(e) => {
                        const prompts = [...draft.prompts]
                        prompts[i] = e.target.value
                        set({ prompts })
                      }}
                      placeholder={`提示词 ${i + 1}`}
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button className="btn" onClick={handleRegen} disabled={busy}>
                  {busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
                  重新生成
                </button>
                {(item.status === 'success' || item.status === 'delisted') && (
                  <button
                    className="btn btn-danger"
                    onClick={handleDelist}
                    disabled={busy || item.status === 'delisted'}
                  >
                    <Trash2 size={15} />
                    {item.status === 'delisted' ? '已下架' : '下架'}
                  </button>
                )}
                {item.rpa_result && (
                  <details className="ml-auto w-full sm:w-auto">
                    <summary className="flex cursor-pointer items-center gap-1.5 text-xs text-muted hover:text-foreground">
                      <Terminal size={14} /> RPA 执行日志
                    </summary>
                    <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-border bg-surface-2 p-3 font-mono text-[11px] leading-relaxed text-slate-300">
                      {(item.rpa_result.steps || []).map((s, i) => (
                        <div key={i}>· {s}</div>
                      ))}
                      {screenshotUrl && (
                        <img src={screenshotUrl} alt="RPA 截图" className="mt-3 w-full rounded-md border border-border" />
                      )}
                    </div>
                  </details>
                )}
              </div>

              {item.status === 'failed' && item.error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2.5 text-sm text-red-300">
                  发布失败：{item.error}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
