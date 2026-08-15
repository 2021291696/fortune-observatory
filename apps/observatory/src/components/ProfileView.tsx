import { Database, LockKey, ShieldCheck } from '@phosphor-icons/react'
import type { SavedReading } from '../types'
import type { ThemeId } from '../themes'
import { SavedReadings } from './SavedReadings'
import { ThemeRemote } from './ThemeRemote'

export function ProfileView({
  activeTheme,
  motionPaused,
  savedReadings,
  onSelectTheme,
  onToggleMotion,
  onRemoveSaved,
  onClearSaved,
}: {
  activeTheme: ThemeId
  motionPaused: boolean
  savedReadings: SavedReading[]
  onSelectTheme: (theme: ThemeId) => void
  onToggleMotion: () => void
  onRemoveSaved: (id: string) => void
  onClearSaved: () => void
}) {
  return <section className="task-view profile-view" id="profile" aria-labelledby="profile-title">
    <header className="task-heading">
      <span>我的</span>
      <h1 id="profile-title">保存、外观与隐私</h1>
    </header>

    <div className="profile-grid">
      <section className="preference-card">
        <div className="card-kicker"><span>外观偏好</span></div>
        <ThemeRemote activeTheme={activeTheme} motionPaused={motionPaused} onSelect={onSelectTheme} onToggleMotion={onToggleMotion} />
      </section>
      <section className="privacy-card" aria-labelledby="privacy-title">
        <div className="card-kicker"><span id="privacy-title">资料怎么处理</span></div>
        <ul>
          <li><LockKey size={20} weight="bold" /><span><strong>出生资料不落盘</strong>刷新或关闭网页后不会保留。</span></li>
          <li><Database size={20} weight="bold" /><span><strong>只保存你主动收藏的结论</strong>最多 24 条，不含出生资料。</span></li>
          <li><ShieldCheck size={20} weight="bold" /><span><strong>计算与主题分离</strong>换皮肤不改变结果。</span></li>
        </ul>
      </section>
    </div>

    <SavedReadings items={savedReadings} onRemove={onRemoveSaved} onClear={onClearSaved} />
  </section>
}
