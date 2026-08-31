import { ChatCircleDots, CheckCircle, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import type { AiExplainResponse, AiExplainSource } from '../types'
import {
  clearCache,
  estimatedProgress,
  joinBackgroundGeneration,
  readCache,
} from './AiExplainPanel'

type Section = {
  id: 'past' | 'now' | 'next'
  heading: string
  question: string
  cacheKey: string
}

export function DomainEssay({
  source,
  sections,
}: {
  source: Omit<AiExplainSource, 'key' | 'title'> & { key: string }
  sections: Section[]
}) {
  const [answers, setAnswers] = useState<Partial<Record<Section['id'], AiExplainResponse>>>({})
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [progress, setProgress] = useState(0)
  const runId = useRef(0)
  const progressTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source.key, sections.map((item) => item.cacheKey + item.question).join('|')])

  function startProgress(startedAt: number) {
    setProgress(estimatedProgress(Date.now() - startedAt))
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = window.setInterval(() => {
      setProgress(estimatedProgress(Date.now() - startedAt))
    }, 150)
  }

  function finishProgress() {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = null
    setProgress(100)
  }

  async function load() {
    const run = ++runId.current
    setError(null)
    const cached = Object.fromEntries(
      sections
        .map((section) => [section.id, readCache(section.cacheKey)?.answer] as const)
        .filter((entry) => entry[1]),
    ) as Partial<Record<Section['id'], AiExplainResponse>>
    if (sections.every((section) => cached[section.id])) {
      setAnswers(cached)
      setIsLoading(false)
      return
    }
    setAnswers({})
    setIsLoading(true)
    const jobs = sections.map((section) =>
      joinBackgroundGeneration(section.cacheKey, section.question, source.contextTokens),
    )
    startProgress(Math.min(...jobs.map((job) => job.startedAt)))
    const results = await Promise.all(jobs.map((job) => job.task))
    if (runId.current !== run) return
    finishProgress()
    const next: Partial<Record<Section['id'], AiExplainResponse>> = {}
    for (let i = 0; i < sections.length; i += 1) {
      const result = results[i]
      if (!result || (typeof result === 'object' && '__failed' in result)) {
        setAnswers({})
        setError(result && typeof result === 'object' && '__failed' in result ? result.message : 'AI 讲解这次没有生成，请稍后重试。')
        setIsLoading(false)
        return
      }
      next[sections[i].id] = result
    }
    setAnswers(next)
    setIsLoading(false)
  }

  function retry() {
    for (const section of sections) clearCache(section.cacheKey)
    void load()
  }

  const ready = sections.every((section) => answers[section.id])
  const now = answers.now

  return <section className="ai-explain-panel domain-essay" aria-label="AI 解读">
    <div className="ai-auto-head">
      <span><ChatCircleDots size={18} weight="fill" /> AI 解读</span>
      {ready && !isLoading && <small>本机缓存 · 24 小时内不重复调用</small>}
    </div>
    {isLoading && <div className="ai-progress" role="status" aria-label={`AI 正在思考，进度 ${progress}%`}>
      <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
      <span>AI 正在结合你的盘思考… {progress}%</span>
    </div>}
    {error && !isLoading && <p className="ai-answer-error" role="alert">
      <WarningCircle size={18} weight="bold" />这一篇没写成。{error}
      <button type="button" className="ai-followup-toggle" onClick={retry}>重试</button>
    </p>}
    {ready && !isLoading && <article className="ai-answer">
      <header><CheckCircle size={21} weight="fill" /><div><strong>AI 解读</strong></div></header>
      {sections.map((section) => {
        const text = answers[section.id]?.summary.text ?? ''
        return <div key={section.id} className="essay-block">
          <h3>{section.heading}</h3>
          {text.split(/\n{2,}/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}
        </div>
      })}
      {now && now.actions.length > 0 && <div>
        <strong>可以先做</strong>
        <ul>{now.actions.map((item) => <li key={`${item.text}-${item.fact_ids.join('-')}`}>{item.text}</li>)}</ul>
      </div>}
      {now && now.caveats.length > 0 && <div className="ai-caveats">
        <strong>注意</strong>
        <ul>{now.caveats.map((item) => <li key={`${item.text}-${item.fact_ids.join('-')}`}>{item.text}</li>)}</ul>
      </div>}
    </article>}
  </section>
}
