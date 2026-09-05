import { API_BASE } from './apiBase'

// 流式解读的前端消费层：SSE 解析 + 跨组件共享的在途流注册表。
// 离开页面不会中断生成（M3 一次批命以分钟计，中断就是白烧钱），
// 同一个 cacheKey 的后来者直接挂到在途流上接着看。
//
// 渲染分两层：text 是已接收的完整文本（缓存/持久化用它），
// displayText 是打字机节奏的显示文本。上游出字是 ~150 字/秒的洪水
// （生产实测），照原速渲染就是"糊一屏"。displayText 按打字机速率放：
// 流式期间恒速 ~80 字/秒（比例控制器会收敛到到达速度，必须硬上限），
// done 之后以加速速率把余量快速放完。
const PACER_RATE_CHARS_PER_SEC = 80
const PACER_DRAIN_CHARS_PER_SEC = 640
const PACER_FRAME_MS = 1000 / 60

export type StreamPhase = 'idle' | 'thinking' | 'streaming' | 'done' | 'error'

export type StreamSnapshot = {
  text: string
  displayText: string
  // 模型思考链（<think> 转播）：不进缓存、不持久化，仅供折叠条展示。
  thinkText: string
  phase: StreamPhase
  error?: string
  sources?: { channel: string; work: string; quote: string }[]
  startedAt: number
}

type StreamEntry = {
  snapshot: StreamSnapshot
  listeners: Set<() => void>
  controller: AbortController
  // 打字机节奏器的 rAF 帧号；null = 未在跑（追平即停，下一个 delta 重启）。
  pacer: number | null
  // 帧间小数步长累积（1.33 字/帧这类非整数速率）。
  pacerAcc: number
  // 思考链的通知合帧（思考按原速转播，一帧最多重渲染一次）。
  thinkFrame: number | null
}

const inflight = new Map<string, StreamEntry>()

function snapshotOf(entry: StreamEntry): StreamSnapshot {
  return entry.snapshot
}

function emit(entry: StreamEntry) {
  entry.listeners.forEach((listener) => listener())
}

function startPacer(entry: StreamEntry) {
  if (entry.pacer !== null) return
  let last = performance.now()
  const frame = (now: number) => {
    entry.pacer = null
    const dt = Math.min(200, now - last) / 1000
    last = now
    const snapshot = entry.snapshot
    const shown = snapshot.displayText.length
    const gap = snapshot.text.length - shown
    if (gap <= 0) return
    // 流式期间恒速可读；大缺口（重连回放追赶）与收尾（done/error）加速放完。
    const draining = snapshot.phase === 'done' || snapshot.phase === 'error'
    const rate = draining || gap > 2000
      ? Math.max(PACER_DRAIN_CHARS_PER_SEC, gap * 2)
      : Math.min(PACER_RATE_CHARS_PER_SEC, gap * 6)
    entry.pacerAcc += rate * dt
    const step = Math.floor(entry.pacerAcc)
    if (step <= 0) {
      startPacer(entry)
      return
    }
    entry.pacerAcc -= step
    const move = Math.min(step, gap)
    entry.snapshot = { ...snapshot, displayText: snapshot.text.slice(0, shown + move) }
    emit(entry)
    startPacer(entry)
  }
  entry.pacer = window.requestAnimationFrame(frame)
}

function flushEmit(entry: StreamEntry) {
  if (entry.thinkFrame !== null) {
    window.cancelAnimationFrame(entry.thinkFrame)
    entry.thinkFrame = null
  }
  emit(entry)
}

// 思考链合帧通知：上游 think 事件同样高频，一帧最多重渲染一次。
function scheduleThinkEmit(entry: StreamEntry) {
  if (entry.thinkFrame !== null) return
  entry.thinkFrame = window.requestAnimationFrame(() => {
    entry.thinkFrame = null
    emit(entry)
  })
}

function handleEvent(entry: StreamEntry, event: { type?: unknown; text?: unknown; detail?: unknown; code?: unknown; sources?: unknown }) {
  if (event.type === 'think' && typeof event.text === 'string') {
    entry.snapshot = { ...entry.snapshot, thinkText: entry.snapshot.thinkText + event.text }
    scheduleThinkEmit(entry)
    return
  }
  if (event.type === 'delta' && typeof event.text === 'string') {
    const first = entry.snapshot.text === ''
    entry.snapshot = { ...entry.snapshot, text: entry.snapshot.text + event.text, phase: 'streaming' }
    startPacer(entry)
    if (first) {
      // thinking→streaming 相位切换立即通知（进度条让位、气泡出现不等帧）。
      flushEmit(entry)
    }
    return
  }
  if (event.type === 'done') {
    const sources = Array.isArray(event.sources)
      ? event.sources.filter((item): item is { channel: string; work: string; quote: string } =>
        Boolean(item && typeof item === 'object' && typeof (item as { work?: unknown }).work === 'string'),
      )
      : undefined
    entry.snapshot = { ...entry.snapshot, phase: 'done', sources }
    flushEmit(entry)
    startPacer(entry) // 把 displayText 追平到全文再停
    inflight.delete(snapshotCacheKeyOf(entry))
    return
  }
  if (event.type === 'error') {
    const detail = typeof event.detail === 'string' ? event.detail.slice(0, 180) : 'AI 解读这次没有生成，请稍后重试。'
    // 内容红线命中（code=safety）：正文已不可信，清空展示层只留错误提示。
    const safety = event.code === 'safety'
    entry.snapshot = {
      ...entry.snapshot,
      text: safety ? '' : entry.snapshot.text,
      displayText: safety ? '' : entry.snapshot.displayText,
      thinkText: safety ? '' : entry.snapshot.thinkText,
      phase: 'error',
      error: detail,
    }
    flushEmit(entry)
    startPacer(entry)
    inflight.delete(snapshotCacheKeyOf(entry))
  }
}

// 反查缓存键：注册表值到键的弱关联（收尾时自清）。
const entryKeys = new WeakMap<StreamEntry, string>()
function snapshotCacheKeyOf(entry: StreamEntry): string {
  return entryKeys.get(entry) ?? ''
}

// 断线续传键：由逻辑请求的稳定要素派生（重试必须携带同一键，服务端据此
// 回放+续播）。清洗出安全字符并附短哈希保唯一。
export function streamKeyOf(...parts: (string | undefined)[]): string {
  const raw = parts.filter((part): part is string => Boolean(part)).join('|')
  let hash = 0
  for (let i = 0; i < raw.length; i++) hash = (hash * 31 + raw.charCodeAt(i)) | 0
  const base = raw.replace(/[^a-zA-Z0-9._-]/g, '-').replace(/-+/g, '-').slice(0, 56)
  return `${base || 'stream'}-${(hash >>> 0).toString(36)}`
}

async function run(entry: StreamEntry, key: string, endpoint: string, body: unknown) {
  // 断流自动重连：跨境长连接会被中间设备间歇掐断（实测 27-95 秒静默 EOF
  // 或 RST）。同 stream_key 重发请求，服务端回放已生成文本再续播——不重复
  // 计费、不重新生成。重连前清空本地文本，服务端会全量回放。
  const resetForReplay = () => {
    entry.snapshot = { ...entry.snapshot, text: '', displayText: '', thinkText: '', phase: 'thinking' }
    flushEmit(entry)
  }
  let reconnects = 0
  while (true) {
    let reconnect = false
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
        flushEmit(entry)
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
          if (!line.startsWith('data:')) continue // ": ping…" 填充心跳注释行
          const payloadText = line.slice(5).trim()
          if (!payloadText || payloadText === '[DONE]') continue
          try {
            handleEvent(entry, JSON.parse(payloadText) as Record<string, unknown>)
          } catch {
            // 单个坏事件直接跳过，不中断整条流。
          }
        }
      }
      if (entry.snapshot.phase === 'done' || entry.snapshot.phase === 'error') return
      reconnect = true // 静默 EOF：连接被中途掐断
    } catch (reason) {
      if (entry.controller.signal.aborted) return
      reconnect = true // 网络异常（RST / 连接重置）
      void reason
    }
    if (!reconnect) return
    if (reconnects >= 2) {
      if (entry.snapshot.phase !== 'done' && entry.snapshot.phase !== 'error') {
        entry.snapshot = { ...entry.snapshot, phase: 'error', error: '连接中断，自动重连仍未恢复，请重试。' }
        flushEmit(entry)
      }
      return
    }
    reconnects += 1
    resetForReplay()
    await new Promise((resolve) => setTimeout(resolve, 600))
  }
  // 收尾：脱离注册表（终态已定，思考合帧若还挂着直接取消）。
  const pendingThinkFrame: number | null = entry.thinkFrame
  if (pendingThinkFrame !== null) {
    window.cancelAnimationFrame(pendingThinkFrame as number)
    entry.thinkFrame = null
  }
  if (inflight.get(key) === entry) inflight.delete(key)
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
    snapshot: { text: '', displayText: '', thinkText: '', phase: 'thinking', startedAt: Date.now() },
    listeners: new Set(),
    controller: new AbortController(),
    pacer: null,
    pacerAcc: 0,
    thinkFrame: null,
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
