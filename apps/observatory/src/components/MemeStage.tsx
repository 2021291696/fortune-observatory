import type { CSSProperties } from 'react'
import type { ThemeConfig } from '../themes'
import { MemeMedia } from './MemeMedia'

export function MemeStage({ theme, motionPaused }: { theme: ThemeConfig; motionPaused: boolean }) {
  return <div className="meme-stage" aria-label={`${theme.label}主题主视觉`}>
    <div className="stage-grid" aria-hidden="true" />
    <p className="stage-callout">{theme.callout}</p>
    <figure className="main-meme">
      <MemeMedia source={theme.mainMedia} eager alt={`${theme.label}高清静态主角`} />
    </figure>
    <div className="meme-stickers" aria-hidden="true">
      {theme.stickers.slice(0, 3).map((source, index) => <figure
        className={`meme-sticker sticker-${index + 1}`}
        style={{ '--sticker-index': index } as CSSProperties}
        key={`${source}-${index}`}
      >
        <MemeMedia source={source} animate={index === 0 && !motionPaused} />
      </figure>)}
    </div>
    <span className="stage-stamp">高清主角 · 动态贴纸</span>
  </div>
}
