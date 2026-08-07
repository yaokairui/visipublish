import { useCallback, useMemo } from 'react'
import { ImagePlus, Loader2, Sparkles, Trash2, UploadCloud } from 'lucide-react'

interface UploadZoneProps {
  files: File[]
  setFiles: (files: File[]) => void
  batchLimit: number
  generating: boolean
  onGenerate: () => void
}

export default function UploadZone({
  files,
  setFiles,
  batchLimit,
  generating,
  onGenerate,
}: UploadZoneProps) {
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files])

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const next = [...files, ...Array.from(incoming)].slice(0, batchLimit)
      setFiles(next)
    },
    [files, batchLimit, setFiles],
  )

  return (
    <section className="card p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">
          <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 font-mono text-xs text-accent">
            1
          </span>
          上传商品图片（可多选）
        </h2>
        {files.length > 0 && (
          <span className="text-xs text-muted">
            已选 <span className="font-mono text-foreground">{files.length}</span> 张
            {files.length >= batchLimit && <span className="ml-1 text-warning">（已达上限）</span>}
          </span>
        )}
      </div>

      <div
        className="mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-surface-2 px-6 py-10 transition-colors hover:border-accent/60"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
        }}
        onClick={() => document.getElementById('file-input')?.click()}
        role="button"
        aria-label="上传商品图片"
      >
        <UploadCloud size={30} className="text-muted" />
        <p className="text-sm text-muted">
          拖拽图片到此处，或 <span className="text-accent">点击选择</span>（jpg / png / webp）
        </p>
        <input
          id="file-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      {previews.length > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
          {files.map((f, i) => (
            <div key={`${f.name}-${i}`} className="group relative overflow-hidden rounded-lg border border-border">
              <img src={previews[i]} alt={f.name} className="aspect-square w-full object-cover" />
              <div className="absolute inset-x-0 bottom-0 truncate bg-black/70 px-2 py-1 text-[11px]">
                {f.name}
              </div>
              <button
                className="absolute right-1 top-1 rounded-md bg-black/60 p-1 text-slate-300 opacity-0 transition-opacity hover:text-red-300 group-hover:opacity-100"
                onClick={() => setFiles(files.filter((_, j) => j !== i))}
                aria-label={`移除 ${f.name}`}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-muted">
          超过单批上限 {batchLimit} 张时将自动截断
        </p>
        <button className="btn btn-primary" onClick={onGenerate} disabled={generating || files.length === 0}>
          {generating ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {generating ? '正在识别并生成标题…' : '开始生成'}
        </button>
      </div>
    </section>
  )
}
