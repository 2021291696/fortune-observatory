import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
// 霞鹜文楷 GB 屏显版（unicode-range 分包：浏览器只拉页面用到的字块）
import 'cn-fontsource-lxgw-wen-kai-gb-screen/font.css'
import './styles.css'
import './theme-styles.css'
import './components.css'
import './task-layout.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
