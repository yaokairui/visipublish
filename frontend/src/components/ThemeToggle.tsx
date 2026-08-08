import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'

declare global {
  interface Window {
    __visipublishTheme?: string
    __vpSetTheme?: (t: 'light' | 'dark') => void
  }
}

export default function ThemeToggle() {
  const [light, setLight] = useState(
    () => (document.documentElement.dataset.theme || window.__visipublishTheme || 'dark') === 'light',
  )

  const toggle = () => {
    const next: 'light' | 'dark' = light ? 'dark' : 'light'
    setLight(!light)
    if (typeof window.__vpSetTheme === 'function') window.__vpSetTheme(next)
  }

  return (
    <button
      type="button"
      className="theme-toggle fixed right-4 top-4 z-50"
      onClick={toggle}
      aria-label={light ? '切换到暗黑模式' : '切换到明亮模式'}
      title={light ? '切换到暗黑模式' : '切换到明亮模式'}
    >
      {light ? <Moon size={20} /> : <Sun size={20} />}
    </button>
  )
}
