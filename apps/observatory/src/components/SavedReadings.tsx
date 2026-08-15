import { Archive, Briefcase, CalendarDots, Heart, Trash } from '@phosphor-icons/react'
import type { SavedReading } from '../types'

const formatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Shanghai',
})

export function SavedReadings({ items, onRemove, onClear }: {
  items: SavedReading[]
  onRemove: (id: string) => void
  onClear: () => void
}) {
  return <section className="saved-section" id="saved">
    <header className="content-heading compact-heading">
      <span>你的保存区</span>
      <h2>只留下你想回看的。</h2>
      <p>你主动保存的命理结果与依据会写入当前浏览器本地存储；不保存出生日期、时间或地点。共享设备上建议不保存，用完后可一键清空。</p>
    </header>
    <div className="saved-panel">
      <div className="saved-toolbar">
        <div><Archive size={22} weight="fill" /><strong>{items.length} 项本地记录</strong></div>
        {items.length > 0 && <button type="button" onClick={() => {
          if (window.confirm('确定清空全部本地保存记录吗？')) onClear()
        }}><Trash size={16} /> 清空全部</button>}
      </div>
      {items.length === 0 ? <div className="saved-empty">
        <Archive size={42} weight="bold" />
        <div><strong>保存区还是空的</strong><p>专项分析和运势结果中都有独立的“保存”按钮。</p></div>
      </div> : <div className="saved-grid">
        {items.map((item) => <article key={item.id}>
          <header>
            <span className={`saved-kind is-${item.kind}`}>{item.kind === 'domain' ? <Briefcase size={14} /> : <CalendarDots size={14} />}{item.kind === 'domain' ? '专项分析' : '时间运势'}</span>
            <button type="button" aria-label={`删除${item.title}`} onClick={() => onRemove(item.id)}><Trash size={17} /></button>
          </header>
          <h3>{item.title}</h3>
          <p>{item.summary}</p>
          <details><summary>查看依据与行动</summary><ul>{item.details.map((detail, index) => <li key={`${detail}-${index}`}>{detail}</li>)}</ul></details>
          <footer><Heart size={13} weight="fill" /><time dateTime={item.savedAt}>{formatter.format(new Date(item.savedAt))}</time></footer>
        </article>)}
      </div>}
    </div>
  </section>
}
