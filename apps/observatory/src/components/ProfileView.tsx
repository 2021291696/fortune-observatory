import { Database, LockKey, ShieldCheck } from '@phosphor-icons/react'
import type { SavedReading } from '../types'
import { readingSystemLabels, readingSystemNotes, type ReadingSystem } from '../readingSystem'
import type { ThemeId } from '../themes'
import { SavedReadings } from './SavedReadings'
import { ThemeRemote } from './ThemeRemote'

const readingSystems: ReadingSystem[] = ['bazi', 'ziwei']

export function ProfileView({
  activeTheme,
  motionPaused,
  savedReadings,
  readingSystem,
  onSelectReadingSystem,
  onSelectTheme,
  onToggleMotion,
  onRemoveSaved,
  onClearSaved,
}: {
  activeTheme: ThemeId
  motionPaused: boolean
  savedReadings: SavedReading[]
  readingSystem: ReadingSystem
  onSelectReadingSystem: (system: ReadingSystem) => void
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
      <section className="preference-card" aria-labelledby="reading-system-title">
        <div className="card-kicker"><span id="reading-system-title">解读体系</span></div>
        <div className="reading-system-picker" role="group" aria-label="选择解读体系">
          {readingSystems.map((system) => <button
            key={system}
            type="button"
            className={readingSystem === system ? 'is-active' : ''}
            aria-pressed={readingSystem === system}
            onClick={() => onSelectReadingSystem(system)}
          >
            {readingSystemLabels[system]}
            <small>{readingSystemNotes[system]}</small>
          </button>)}
        </div>
        <p className="reading-system-note">当前按「{readingSystemLabels[readingSystem]}」解读：{readingSystemNotes[readingSystem]}。运势与问事都只出这一个体系的解读。</p>
        <p className="reading-system-note is-muted">换一个体系后，问事和运势会按新体系重新解读（首次生成需要等一会儿）；已保存的结论不受影响。</p>
      </section>
      <section className="preference-card">
        <div className="card-kicker"><span>外观偏好</span></div>
        <ThemeRemote activeTheme={activeTheme} motionPaused={motionPaused} onSelect={onSelectTheme} onToggleMotion={onToggleMotion} />
      </section>
      <section className="privacy-card" aria-labelledby="privacy-title">
        <div className="card-kicker"><span id="privacy-title">资料怎么处理</span></div>
        <ul>
          <li><LockKey size={20} weight="bold" /><span><strong>本机保存，计算时会发送</strong>排盘和运势会发到服务器处理，用完不保存；可在命盘页改名或删除。</span></li>
          <li><Database size={20} weight="bold" /><span><strong>收藏结论独立保存</strong>最多 24 条，不含出生资料。</span></li>
          <li><ShieldCheck size={20} weight="bold" /><span><strong>计算与主题分离</strong>换皮肤不改变结果。</span></li>
        </ul>
      </section>
    </div>

    <SavedReadings items={savedReadings} onRemove={onRemoveSaved} onClear={onClearSaved} />
  </section>
}
