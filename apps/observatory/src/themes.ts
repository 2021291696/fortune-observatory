import phoebe01 from './assets/memes/phoebe/phoebe-01.mp4'
import phoebe02 from './assets/memes/phoebe/phoebe-02.mp4'
import phoebe03 from './assets/memes/phoebe/phoebe-03.mp4'
import phoebe04 from './assets/memes/phoebe/phoebe-04.mp4'
import phoebe05 from './assets/memes/phoebe/phoebe-05.mp4'
import phoebe06 from './assets/memes/phoebe/phoebe-06.mp4'
import phoebeThumb from './assets/memes/phoebe/thumb.jpg'
import phoebeHero from './assets/memes/phoebe/phoebe-hero-hd-v2.webp'
import ggbond01 from './assets/memes/ggbond/ggbond-01.mp4'
import ggbond02 from './assets/memes/ggbond/ggbond-02.mp4'
import ggbond03 from './assets/memes/ggbond/ggbond-03.mp4'
import ggbondThumb from './assets/memes/ggbond/thumb.jpg'
import ggbondHero from './assets/memes/ggbond/ggbond-hero-hd-v2.webp'
import nailong01 from './assets/memes/nailong/nailong-01.mp4'
import nailong02 from './assets/memes/nailong/nailong-02.mp4'
import nailongP02 from './assets/memes/nailong/nailong-02.png'
import nailongP03 from './assets/memes/nailong/nailong-03.png'
import nailongP04 from './assets/memes/nailong/nailong-04.png'
import nailongP05 from './assets/memes/nailong/nailong-05.png'
import nailongP06 from './assets/memes/nailong/nailong-06.png'
import nailongP07 from './assets/memes/nailong/nailong-07.png'
import nailongP08 from './assets/memes/nailong/nailong-08.png'
import nailongThumb from './assets/memes/nailong/thumb.png'
import nailongHero from './assets/memes/nailong/nailong-hero-hd-v2.webp'
import kawaii01 from './assets/memes/kawaii/kawaii-01.mp4'
import kawaiiP01 from './assets/memes/kawaii/kawaii-01.png'
import kawaiiP02 from './assets/memes/kawaii/kawaii-02.png'
import kawaiiP03 from './assets/memes/kawaii/kawaii-03.png'
import kawaiiP04 from './assets/memes/kawaii/kawaii-04.png'
import kawaiiP05 from './assets/memes/kawaii/kawaii-05.png'
import kawaiiP06 from './assets/memes/kawaii/kawaii-06.png'
import kawaiiP07 from './assets/memes/kawaii/kawaii-07.png'
import kawaiiP08 from './assets/memes/kawaii/kawaii-08.png'
import kawaiiP09 from './assets/memes/kawaii/kawaii-09.png'
import kawaiiThumb from './assets/memes/kawaii/thumb.png'
import kawaiiHero from './assets/memes/kawaii/kawaii-hero-hd-v2.webp'
import ggbondPoster01 from './assets/memes/posters/ggbond-ggbond-01.webp'
import ggbondPoster02 from './assets/memes/posters/ggbond-ggbond-02.webp'
import ggbondPoster03 from './assets/memes/posters/ggbond-ggbond-03.webp'
import kawaiiPoster01 from './assets/memes/posters/kawaii-kawaii-01.webp'
import nailongPoster01 from './assets/memes/posters/nailong-nailong-01.webp'
import nailongPoster02 from './assets/memes/posters/nailong-nailong-02.webp'
import phoebePoster01 from './assets/memes/posters/phoebe-phoebe-01.webp'
import phoebePoster02 from './assets/memes/posters/phoebe-phoebe-02.webp'
import phoebePoster03 from './assets/memes/posters/phoebe-phoebe-03.webp'
import phoebePoster04 from './assets/memes/posters/phoebe-phoebe-04.webp'
import phoebePoster05 from './assets/memes/posters/phoebe-phoebe-05.webp'
import phoebePoster06 from './assets/memes/posters/phoebe-phoebe-06.webp'

export type ThemeId = 'phoebe' | 'ggbond' | 'nailong' | 'kawaii' | 'shuffle'
export type PaletteId = Exclude<ThemeId, 'shuffle'>
export type LayoutId = 'stage' | 'desk'
export type MotionId = 'float' | 'hero' | 'squash' | 'scatter'

export type ThemeConfig = {
  id: ThemeId
  label: string
  navLabel: string
  palette: PaletteId
  layout: LayoutId
  motion: MotionId
  eyebrow: string
  headline: string
  deck: string
  callout: string
  thumbnail: string
  mainMedia: string
  stickers: string[]
}

const baseThemes: Record<PaletteId, ThemeConfig> = {
  phoebe: {
    id: 'phoebe', label: '菲比啾比', navLabel: '啾比', palette: 'phoebe', layout: 'desk', motion: 'float',
    eyebrow: 'Q 舞台正在占领网页', headline: '先别懂事，先看看今天。',
    deck: '填完出生信息，今日运势自动出现。其他周期等你点名。', callout: '啾比正在旁观你的输入',
    thumbnail: phoebeThumb, mainMedia: phoebeHero, stickers: [phoebe03, phoebe01, phoebe02, phoebe04, phoebe05, phoebe06],
  },
  ggbond: {
    id: 'ggbond', label: 'GGBond', navLabel: 'GG', palette: 'ggbond', layout: 'stage', motion: 'hero',
    eyebrow: '英雄频道插播中', headline: '先排盘，再决定今天救不救世界。',
    deck: '排盘完成就自动生成今日运势，专项与其他周期由你决定。', callout: '英雄待机，不影响计算',
    thumbnail: ggbondThumb, mainMedia: ggbondHero, stickers: [ggbond01, ggbond02, ggbond03, ggbondThumb],
  },
  nailong: {
    id: 'nailong', label: '奶龙', navLabel: '奶龙', palette: 'nailong', layout: 'stage', motion: 'squash',
    eyebrow: '稀有皮肤已加载', headline: '今天，看看会遇到什么。',
    deck: '填完出生信息，今日运势自动出现。其他周期等你点名。', callout: '奶龙已接管大屏',
    thumbnail: nailongThumb, mainMedia: nailongHero, stickers: [nailong01, nailong02, nailongP02, nailongP03, nailongP04, nailongP05, nailongP06, nailongP07, nailongP08],
  },
  kawaii: {
    id: 'kawaii', label: '可爱反应图', navLabel: '可爱', palette: 'kawaii', layout: 'desk', motion: 'scatter',
    eyebrow: '反应图桌面已失控', headline: '命运正在加载你的反应图。',
    deck: '大主角保持高清静态，小贴纸负责动态围观；计算结果仍然逐条可追溯。', callout: '当前反应：假装冷静',
    thumbnail: kawaiiThumb, mainMedia: kawaiiHero, stickers: [kawaii01, kawaiiP01, kawaiiP02, kawaiiP03, kawaiiP04, kawaiiP05, kawaiiP06, kawaiiP07, kawaiiP08, kawaiiP09],
  },
}

export const themeOrder: ThemeId[] = ['phoebe', 'ggbond', 'nailong', 'kawaii', 'shuffle']
export const themeChoices = themeOrder.map((id) => id === 'shuffle'
  ? { id, label: '随机混合', navLabel: '混合', thumbnail: kawaiiP07 }
  : baseThemes[id])

function mulberry32(seed: number) {
  return () => {
    let value = seed += 0x6D2B79F5
    value = Math.imul(value ^ value >>> 15, value | 1)
    value ^= value + Math.imul(value ^ value >>> 7, value | 61)
    return ((value ^ value >>> 14) >>> 0) / 4294967296
  }
}

function pick<T>(items: T[], random: () => number) {
  return items[Math.floor(random() * items.length)]
}

export function resolveTheme(id: ThemeId, seed: number): ThemeConfig {
  if (id !== 'shuffle') return baseThemes[id]
  const random = mulberry32(seed)
  const sources = Object.values(baseThemes)
  const palette = pick(sources, random).palette
  const layout = pick<LayoutId>(['stage', 'desk'], random)
  const motion = pick<MotionId>(['float', 'hero', 'squash', 'scatter'], random)
  const mainMedia = pick(sources, random).mainMedia
  const categoryPicks = sources.map((theme) => pick(theme.stickers, random))
  return {
    id: 'shuffle', label: '四类随机混合', navLabel: '混合', palette, layout, motion,
    eyebrow: `随机种子 ${String(seed).slice(-5)} 正在生效`,
    headline: '本页精神状态，由随机数决定。',
    deck: '四类高清主角与动态贴纸重新洗牌，已填内容、命盘和保存结果都不会动。',
    callout: '这次组合只属于你', thumbnail: kawaiiP07, mainMedia,
    stickers: categoryPicks.concat(pick(sources, random).stickers.slice(0, 2)),
  }
}

export function isVideo(source: string) {
  return source.toLowerCase().includes('.mp4')
}

const videoPosters = new Map<string, string>([
  [ggbond01, ggbondPoster01], [ggbond02, ggbondPoster02], [ggbond03, ggbondPoster03],
  [kawaii01, kawaiiPoster01], [nailong01, nailongPoster01], [nailong02, nailongPoster02],
  [phoebe01, phoebePoster01], [phoebe02, phoebePoster02], [phoebe03, phoebePoster03],
  [phoebe04, phoebePoster04], [phoebe05, phoebePoster05], [phoebe06, phoebePoster06],
])

export function posterForMedia(source: string) {
  return isVideo(source) ? videoPosters.get(source) : source
}
