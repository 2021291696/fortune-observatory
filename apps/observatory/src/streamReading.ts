import { API_BASE } from './apiBase'

// 流式解读的前端消费层：SSE 解析 + 跨组件共享的在途流注册表。
// 离开页面不会中断生成（M3 一次批命以分钟计，中断就是白烧钱），
// 同一个 cacheKey 的后来者直接挂到在途流上接着看。

export type StreamPhase = 'idle' | 'thinking' | 'streaming' | 'done' | 'error'

export type StreamSnapshot = {
  text: string
  phase: StreamPhase
  error?: string
  sources?: { channel: string; work: string; quote: string }[]
  startedAt: number
}

type StreamEntry = {
  snapshot: StreamSnapshot
  listeners: Set<() => void>
  controller: AbortController
}

const inflight = new Map<string, StreamEntry>()

function snapshotOf(entry: StreamEntry): StreamSnapshot {
  return entry.snapshot
}

function emit(entry: StreamEntry) {
  entry.listeners.forEach((listener) => listener())
}

function handleEvent(entry: StreamEntry, event: { type?: unknown; text?: unknown; detail?: unknown; sources?: unknown }) {
  if (event.type === 'delta' && typeof event.text === 'string') {
    entry.snapshot = { ...entry.snapshot, text: entry.snapshot.text + event.text, phase: 'streaming' }
    emit(entry)
    return
  }
  if (event.type === 'done') {
    const sources = Array.isArray(event.sources)
      ? event.sources.filter((item): item is { channel: string; work: string; quote: string } =>
        Boolean(item && typeof item === 'object' && typeof (item as { work?: unknown }).work === 'string'),
      )
      : undefined
    entry.snapshot = { ...entry.snapshot, phase: 'done', sources }
    emit(entry)
    inflight.delete(snapshotCacheKeyOf(entry))
    return
  }
  if (event.type === 'error') {
    const detail = typeof event.detail === 'string' ? event.detail.slice(0, 180) : 'AI 解读这次没有生成，请稍后重试。'
    entry.snapshot = { ...entry.snapshot, phase: 'error', error: detail }
    emit(entry)
    inflight.delete(snapshotCacheKeyOf(entry))
  }
}

// 反查缓存键：注册表值到键的弱关联（收尾时自清）。
const entryKeys = new WeakMap<StreamEntry, string>()
function snapshotCacheKeyOf(entry: StreamEntry): string {
  return entryKeys.get(entry) ?? ''
}

async function run(entry: StreamEntry, key: string, endpoint: string, body: unknown) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { accept: 'text/event-stream', 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: entry.controller.signal,
      credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
    })
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null)
      const detail = payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail?: unknown }).detail).slice(0, 180)
        : 'AI 解读这次没有生成，请稍后重试。'
      entry.snapshot = { ...entry.snapshot, phase: 'error', error: detail }
      emit(entry)
      return
    }
    if (!response.body) throw new Error('当前浏览器不支持流式读取。')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let newlineIndex = buffer.indexOf('\n')
      while (newlineIndex >= 0) {
        const line = buffer.slice(0, newlineIndex).trim()
        buffer = buffer.slice(newlineIndex + 1)
        newlineIndex = buffer.indexOf('\n')
        if (!line.startsWith('data:')) continue // ": ping" 心跳注释行
        const payloadText = line.slice(5).trim()
        if (!payloadText || payloadText === '[DONE]') continue
        try {
          handleEvent(entry, JSON.parse(payloadText) as Record<string, unknown>)
        } catch {
          // 单个坏事件直接跳过，不中断整条流。
        }
      }
    }
    if (entry.snapshot.phase !== 'done' && entry.snapshot.phase !== 'error') {
      entry.snapshot = { ...entry.snapshot, phase: 'error', error: '连接中断，请重试。' }
      emit(entry)
    }
  } catch (reason) {
    if (entry.controller.signal.aborted) return
    entry.snapshot = {
      ...entry.snapshot,
      phase: 'error',
      error: reason instanceof Error ? reason.message.slice(0, 180) : 'AI 解读这次没有生成，请稍后重试。',
    }
    emit(entry)
  } finally {
    if (inflight.get(key) === entry) inflight.delete(key)
  }
}

export type StreamHandle = {
  subscribe: (listener: () => void) => () => void
  getSnapshot: () => StreamSnapshot
}

export function joinStream(key: string, endpoint: string, body: unknown): StreamHandle {
  const existing = inflight.get(key)
  if (existing) {
    return { subscribe: existingSubscribe(existing), getSnapshot: () => snapshotOf(existing) }
  }
  const entry: StreamEntry = {
    snapshot: { text: '', phase: 'thinking', startedAt: Date.now() },
    listeners: new Set(),
    controller: new AbortController(),
  }
  entryKeys.set(entry, key)
  inflight.set(key, entry)
  void run(entry, key, endpoint, body)
  return { subscribe: existingSubscribe(entry), getSnapshot: () => snapshotOf(entry) }
}

function existingSubscribe(entry: StreamEntry) {
  return (listener: () => void) => {
    entry.listeners.add(listener)
    return () => entry.listeners.delete(listener)
  }
}
