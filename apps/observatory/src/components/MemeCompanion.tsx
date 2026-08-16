import type { ThemeConfig } from '../themes'
import { MemeMedia } from './MemeMedia'

/** Mobile-only sticker pair echoing the theme's meme stage inside result cards. */
export function MemeCompanion({ theme }: { theme: ThemeConfig }) {
  const first = theme.stickers[1] ?? theme.mainMedia
  const second = theme.stickers[2] ?? theme.stickers[0] ?? theme.mainMedia
  return <div className="meme-companion" aria-hidden="true">
    <MemeMedia source={first} className="companion-sticker is-a" />
    <MemeMedia source={second} className="companion-sticker is-b" />
  </div>
}
