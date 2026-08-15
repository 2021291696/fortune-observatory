import { ChatCircleDots, StarFour, Sun, UserCircle } from '@phosphor-icons/react'

export type AppView = 'today' | 'ask' | 'chart' | 'profile'

const views = [
  { id: 'today', label: '今日', hint: '先看重点', icon: Sun },
  { id: 'ask', label: '问事', hint: '具体问题', icon: ChatCircleDots },
  { id: 'chart', label: '命盘', hint: '查看依据', icon: StarFour },
  { id: 'profile', label: '我的', hint: '保存与设置', icon: UserCircle },
] as const

export function viewFromHash(hash = window.location.hash): AppView {
  const value = hash.replace(/^#/, '')
  if (value === 'ask' || value === 'analysis' || value === 'fortune') return 'ask'
  if (value === 'chart') return 'chart'
  if (value === 'profile' || value === 'saved') return 'profile'
  return 'today'
}

export function AppNavigation({ activeView, onNavigate }: {
  activeView: AppView
  onNavigate: (view: AppView) => void
}) {
  return <nav className="primary-nav" aria-label="核心功能">
    {views.map(({ id, label, hint, icon: Icon }) => <a
      key={id}
      className={activeView === id ? 'is-active' : ''}
      href={`#${id}`}
      aria-current={activeView === id ? 'page' : undefined}
      onClick={() => onNavigate(id)}
    >
      <Icon size={22} weight={activeView === id ? 'fill' : 'bold'} />
      <span><strong>{label}</strong><small>{hint}</small></span>
    </a>)}
  </nav>
}
