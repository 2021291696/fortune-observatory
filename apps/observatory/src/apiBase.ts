// 生产同域反代（nginx /api → 后端）；相对路径不依赖构建时 env，跨境主域同源直达。
// 仅本地 dev 无 VITE_API_BASE 时落到 127.0.0.1:8000。
export const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD
  ? '/api'
  : 'http://127.0.0.1:8000')
