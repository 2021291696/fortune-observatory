import { Pause, Play, Shuffle } from '@phosphor-icons/react'
import { themeChoices, type ThemeId } from '../themes'

export function ThemeRemote({ activeTheme, motionPaused, onSelect, onToggleMotion }: {
  activeTheme: ThemeId
  motionPaused: boolean
  onSelect: (theme: ThemeId) => void
  onToggleMotion: () => void
}) {
  return <aside className="theme-remote" aria-label="切换页面主题">
    <span className="remote-label">换个精神状态</span>
    <div className="remote-options" role="group" aria-label="五套主题">
      {themeChoices.map((theme) => <button
        type="button"
        key={theme.id}
        className={activeTheme === theme.id ? 'is-active' : ''}
        aria-pressed={activeTheme === theme.id}
        title={theme.id === 'shuffle' && activeTheme === 'shuffle' ? '再次点击重新混合' : `切换到${theme.label}`}
        onClick={() => onSelect(theme.id as ThemeId)}
      >
        {theme.id === 'shuffle'
          ? <span className="remote-shuffle"><Shuffle size={20} weight="bold" /></span>
          : <img src={theme.thumbnail} alt="" />}
        <span>{theme.navLabel}</span>
      </button>)}
    </div>
    <button
      type="button"
      className="motion-toggle"
      aria-pressed={!motionPaused}
      aria-label="动态贴纸动画"
      title={motionPaused ? '播放动态贴纸' : '暂停动态贴纸'}
      onClick={onToggleMotion}
    >
      {motionPaused ? <Play size={19} weight="fill" /> : <Pause size={19} weight="fill" />}
      <span>{motionPaused ? '播放动效' : '暂停动效'}</span>
    </button>
  </aside>
}
