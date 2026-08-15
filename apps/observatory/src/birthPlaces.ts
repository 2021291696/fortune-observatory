export type BirthPlace = {
  id: string
  name: string
  geonameId: number
  latitude: number
  longitude: number
  timezoneId: 'Asia/Shanghai'
  featureCode: 'PPLC' | 'PPLA' | 'PPLA2'
  sourceModified: string
}

export const birthPlaceSource = {
  name: 'GeoNames CN.zip',
  url: 'https://download.geonames.org/export/dump/CN.zip',
  licenseUrl: 'https://download.geonames.org/export/dump/readme.txt',
  license: 'CC BY 4.0',
  snapshotAt: '2026-07-28T11:53:24+08:00',
  bytes: 32_069_311,
  sha256: '86d8ffd2d4d12bfeae7d15c30d3b0a2ec157736c7276925005276d11342881cf',
  coordinateKind: 'WGS84 representative point',
} as const

export const birthPlaces: BirthPlace[] = [
  { id: 'beijing', name: '北京', geonameId: 1816670, latitude: 39.9075, longitude: 116.39723, timezoneId: 'Asia/Shanghai', featureCode: 'PPLC', sourceModified: '2025-12-15' },
  { id: 'shanghai', name: '上海', geonameId: 1796236, latitude: 31.22222, longitude: 121.45806, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'guangzhou', name: '广州', geonameId: 1809858, latitude: 23.11667, longitude: 113.25, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'shenzhen', name: '深圳', geonameId: 1795565, latitude: 22.54554, longitude: 114.0683, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA2', sourceModified: '2025-10-22' },
  { id: 'chengdu', name: '成都', geonameId: 1815286, latitude: 30.66667, longitude: 104.06667, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'chongqing', name: '重庆', geonameId: 1814906, latitude: 29.56026, longitude: 106.55771, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'wuhan', name: '武汉', geonameId: 1791247, latitude: 30.58333, longitude: 114.26667, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'xian', name: '西安', geonameId: 1790630, latitude: 34.25833, longitude: 108.92861, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'hangzhou', name: '杭州', geonameId: 1808926, latitude: 30.29365, longitude: 120.16142, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'nanjing', name: '南京', geonameId: 1799962, latitude: 32.06167, longitude: 118.77778, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'changsha', name: '长沙', geonameId: 1815577, latitude: 28.19874, longitude: 112.97087, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
  { id: 'tianjin', name: '天津', geonameId: 1792947, latitude: 39.14222, longitude: 117.17667, timezoneId: 'Asia/Shanghai', featureCode: 'PPLA', sourceModified: '2026-04-13' },
]
