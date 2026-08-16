import { Pause, Play, Shuffle } from '@phosphor-icons/react'
import { posterForMedia, themeChoices, type ThemeConfig, type ThemeId } from '../themes'

function previewStickers(theme: ThemeConfig) {
  return theme.stickers.slice(1, 3).map(posterForMedia).filter((source): source is string => Boolean(source))
}

export function ThemeRemote({ activeTheme, motionPaused, onSelect, onToggleMotion }: {
  activeTheme: ThemeId
  motionPaused: boolean
  onSelect: (theme: ThemeId) => void
  onToggleMotion: () => void
}) {
  return <aside className="theme-remote" aria-label="切换页面主题">
    <span className="remote-label">换个精神状态</span>
    <div className="remote-options" role="group" aria-label="五套主题">
      {themeChoices.map((theme) => {
        const isActive = activeTheme === theme.id
        if (theme.id === 'shuffle') {
          return <button
            type="button"
            key={theme.id}
            className={`theme-card theme-card-shuffle${isActive ? ' is-active' : ''}`}
            aria-pressed={isActive}
            title={isActive ? '再次点击重新混合' : '切换到随机混合'}
            onClick={() => onSelect('shuffle')}
          >
            <span className="remote-shuffle"><Shuffle size={18} weight="bold" /></span>
            <span className="theme-card-name">混合 · 四套随机组合</span>
          </button>
        }
        const config = theme as ThemeConfig
        return <button
          type="button"
          key={theme.id}
          className={`theme-card${isActive ? ' is-active' : ''}`}
          data-palette={config.palette}
          aria-pressed={isActive}
          title={`切换到${config.label}`}
          onClick={() => onSelect(config.id)}
        >
          <span className="theme-card-stage">
            <img className="theme-card-hero" src={config.thumbnail} alt="" />
            {previewStickers(config).map((source) => <img key={source} className="theme-card-sticker" src={source} alt="" />)}
          </span>
          <span className="theme-card-name">{config.navLabel}</span>
        </button>
      })}
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
