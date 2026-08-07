import type { Config, Item, PublishStatus, ReviewPatch } from './types'

let sessionId = ''

export function setSession(id: string) {
  sessionId = id
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...((init?.headers as Record<string, string>) || {}),
  }
  if (sessionId) headers['X-Session-Id'] = sessionId
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  createSession: () => req<{ session_id: string }>('/api/session', { method: 'POST' }),
  config: () => req<Config>('/api/config'),
  listItems: () => req<{ items: Item[] }>('/api/items'),
  generate: (files: File[]) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return req<{ items: Item[] }>('/api/generate', { method: 'POST', body: fd })
  },
  review: (id: string, patch: ReviewPatch) =>
    req<{ item: Item }>(`/api/items/${id}/review`, json(patch)),
  regen: (id: string) => req<{ item: Item }>(`/api/items/${id}/regen`, { method: 'POST' }),
  delist: (id: string) =>
    req<{ ok: boolean; message: string }>(`/api/items/${id}/delist`, { method: 'POST' }),
  publish: (itemIds: string[]) =>
    req<{ job_id: string }>('/api/publish', json({ item_ids: itemIds })),
  publishStatus: (jobId: string) => req<PublishStatus>(`/api/publish/${jobId}`),
  clearSession: () => req<{ ok: boolean }>('/api/session', { method: 'DELETE' }),
}
