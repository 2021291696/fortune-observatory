export const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD
  ? 'https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/destiny'
  : 'http://127.0.0.1:8000')
