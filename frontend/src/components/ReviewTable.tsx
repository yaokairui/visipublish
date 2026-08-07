import { ListChecks } from 'lucide-react'
import type { Config, Item, ReviewPatch } from '../types'
import ItemRow from './ItemRow'

interface ReviewTableProps {
  items: Item[]
  config: Config
  selectedIds: Set<string>
  onToggle: (id: string) => void
  onToggleAll: (ids: string[]) => void
  onReview: (id: string, patch: ReviewPatch) => void
  onRegen: (id: string) => void
  onDelist: (id: string) => void
}

export default function ReviewTable({
  items,
  config,
  selectedIds,
  onToggle,
  onToggleAll,
  onReview,
  onRegen,
  onDelist,
}: ReviewTableProps) {
  const selectable = items.filter((it) => it.status !== 'skipped')
  const allSelected = selectable.length > 0 && selectable.every((it) => selectedIds.has(it.id))

  return (
    <section className="mt-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 font-mono text-xs text-accent">
            2
          </span>
          批量审核队列
          <ListChecks size={17} className="text-muted" />
        </h2>
        <div className="flex items-center gap-3 text-xs text-muted">
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-green-500"
              checked={allSelected}
              onChange={() => onToggleAll(selectable.map((it) => it.id))}
            />
            全选
          </label>
          <span>
            已勾选 <span className="font-mono text-foreground">{selectedIds.size}</span> / {items.length}
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {items.map((it, i) => (
          <ItemRow
            key={it.id}
            item={it}
            index={i}
            config={config}
            selected={selectedIds.has(it.id)}
            onToggle={() => onToggle(it.id)}
            onReview={onReview}
            onRegen={onRegen}
            onDelist={onDelist}
          />
        ))}
      </div>
    </section>
  )
}
