export type Pillars = { year: string; month: string; day: string; hour: string }

export type VerificationStatus = 'verified' | 'ambiguous' | 'unsupported'
export type Relation = 'branch_clash' | 'branch_combination' | 'branch_same'

export type TransitFact = {
  fact_id: string
  relation: Relation
  natal_pillar: string
  transit_pillar: string
}

export type ChartResponse = {
  bazi: {
    profile_id: string
    input_time_basis: 'civil' | 'apparent_solar'
    apparent_solar_source: 'provided' | 'jpl_de440s' | 'civil'
    calculation_datetime: string
    lunar_date: string
    pillars: Pillars
    pillar_details: Array<{
      pillar: string
      ten_god: string
      hidden_stems: Array<{ stem: string; ten_god: string }>
      nayin: string
    }>
    great_luck_start: { years: number; months: number; days: number; direction: string; first_pillar: string }
    great_luck_periods: Array<{ pillar: string; start_datetime: string; end_datetime: string; start_age: number; end_age: number }>
    verification_status: VerificationStatus
  }
  ziwei: {
    life_branch: string
    body_branch: string
    five_elements_bureau: number
    year_stem: string
    birth_mutagens: Array<{ star: string; mutagen: string }>
    verification_status: VerificationStatus
    palaces: Array<{
      name: string
      stem: string
      branch: string
      is_body_palace: boolean
      decadal_range: [number, number]
      minor_limit_ages: number[]
      major_stars: string[]
      major_star_brightness: [string, string][]
      minor_stars: string[]
    }>
    flying_mutagens?: Array<{
      from_branch: string
      stem: string
      mutagen: string
      star: string
      to_branch: string
      is_self: boolean
    }>
  }
  qizheng: {
    profile_id: string
    ephemeris_id: string
    ephemeris_datetime: string
    bodies: Array<{
      body: 'sun' | 'moon' | 'mercury' | 'venus' | 'mars' | 'jupiter' | 'saturn'
      longitude_deg: number
      latitude_deg: number
      longitude_rate_deg_per_day: number
      motion: 'direct' | 'retrograde'
    }>
    traditional?: {
      profile_id: string
      anchor: 'j2000_mean_ecliptic'
      bodies: Array<{
        body: 'sun' | 'moon' | 'mercury' | 'venus' | 'mars' | 'jupiter' | 'saturn' | 'rahu' | 'ketu' | 'apogee' | 'ziqi'
        longitude_deg: number
        longitude_rate_deg_per_day: number
        motion: 'direct' | 'retrograde'
        mansion: string
        mansion_offset_deg: number
      }>
      houses?: { life_branch: string; body_branch: string; houses: Array<[string, string]> }
      notes: string[]
      scope_limits: string[]
      verification_status: VerificationStatus
    }
    scope_limits: string[]
    verification_status: VerificationStatus
  }
  time_trace: {
    timezone_id: string
    tzdb_version: string
    resolved_fold: 0 | 1
    longitude: number
    latitude: number
    civil_datetime: string
    utc_datetime: string
    local_mean_solar_datetime: string
    apparent_solar_datetime: string | null
    apparent_solar_source: 'provided' | 'jpl_de440s' | 'civil'
    ephemeris_id: string
    ephemeris_sha256: string
  }
  natal_insights: Array<{ insight_id: string; title: string; summary: string; action: string; fact_ids: string[] }>
  trace_id: string
  ai_contexts: Partial<Record<AnalysisDomain | 'ziwei', AiContextBundle>>
}

export type ZiweiMutagenPlacement = {
  star: string
  mutagen: string
  palace_branch: string
  palace_name: string
}

export type ZiweiYearly = {
  year_pillar: string
  nominal_age: number
  life_branch: string
  yearly_mutagens: ZiweiMutagenPlacement[]
  decadal: {
    branch: string
    stem: string
    start_age: number
    end_age: number
    is_childhood: boolean
    mutagens: ZiweiMutagenPlacement[]
  }
  flowing_stars: Array<{ star: string; branch: string }>
}

export type DailyTransitResponse = {
  transit: {
    transit_date: string
    day_pillar: string
    facts: TransitFact[]
    verification_status: VerificationStatus
  }
  trace_id: string
  ziwei_yearly?: ZiweiYearly | null
  ai_context: AiContextBundle | null
}

export type TransitWindowResponse = {
  transit: {
    start_date: string
    end_date: string
    daily: Array<{
      transit_date: string
      day_pillar: string
      facts: TransitFact[]
      verification_status: VerificationStatus
    }>
    verification_status: VerificationStatus
  }
  trace_id: string
  ai_context: AiContextBundle | null
}

export type TransitResponse = {
  transit: {
    transit_date: string
    layers: Array<{
      period: 'great_luck' | 'year' | 'month' | 'day'
      pillar: string
      facts: TransitFact[]
    }>
    ziwei_annual: {
      target_date: string
      year_pillar: string
      life_branch: string
      palaces: Array<{ name: string; branch: string }>
      verification_status: VerificationStatus
    }
    signals: Array<{
      signal_id: string
      system: 'bazi' | 'ziwei' | 'qizheng'
      direction: 'support' | 'tension' | 'neutral'
      strength: 'core' | 'secondary' | 'edge'
      rule_id: string
      fact_ids: string[]
    }>
    insights: Array<{ insight_id: string; title: string; summary: string; action: string; fact_ids: string[] }>
    verification_status: VerificationStatus
  }
  trace_id: string
  ai_context: AiContextBundle | null
}

export const fortuneScopes = [
  ['today', '今日'],
  ['tomorrow', '明日'],
  ['thisWeek', '本周'],
  ['nextWeek', '下周'],
  ['thisMonth', '本月'],
  ['nextMonth', '下月'],
] as const

export type FortuneScope = typeof fortuneScopes[number][0]

export const analysisDomains = [
  ['health', '健康'],
  ['relationship', '姻缘'],
  ['career', '事业'],
  ['wealth', '财运'],
] as const

export type AnalysisDomain = typeof analysisDomains[number][0]

export type SaveDraft = {
  kind: 'domain' | 'fortune'
  title: string
  summary: string
  details: string[]
  userName?: string
}

export type SavedReading = SaveDraft & {
  id: string
  savedAt: string
}

export type AiFact = { id: string; text: string }

export type AiContextBundle = { token: string; facts: AiFact[] }

export type AiExplainSource = {
  key: string
  kind: 'domain' | 'fortune'
  title: string
  summary: string
  facts: AiFact[]
  contextTokens: string[]
}

export type AiGroundedClaim = { text: string; fact_ids: string[] }

export type AiExplainResponse = {
  summary: AiGroundedClaim
  actions: AiGroundedClaim[]
  caveats: AiGroundedClaim[]
}
