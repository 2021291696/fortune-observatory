import { useMemo, useState, type FormEvent } from 'react'
import { ArrowRight, LockKey, MapPin, PencilSimple, SpinnerGap, Trash, XCircle } from '@phosphor-icons/react'
import { birthPlaces, type BirthPlace } from '../birthPlaces'
import type { ThemeConfig } from '../themes'
import { MemeMedia } from './MemeMedia'

const defaultPlace = birthPlaces[0]

export type BirthInitial = {
  civilDate: string
  civilTime: string
  sexForRule: string
  placeId: string
  longitude: string
  latitude: string
}

export type SummaryInput = {
  date: string
  time: string
  place: string
  sex: string
}

export function BirthForm({ isSubmitting, error, onSubmit, onClear, onCancel, hasChart = false, initial }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
  onCancel?: () => void
  hasChart?: boolean
  initial?: BirthInitial
}) {
  const [placeId, setPlaceId] = useState(initial?.placeId ?? defaultPlace.id)
  const [longitude, setLongitude] = useState(initial?.longitude ?? '')
  const [latitude, setLatitude] = useState(initial?.latitude ?? '')
  const isManual = placeId === 'manual'

  const grouped = useMemo(() => {
    const groups: { province: string; places: BirthPlace[] }[] = []
    for (const place of birthPlaces) {
      const last = groups[groups.length - 1]
      if (last && last.province === place.province) last.places.push(place)
      else groups.push({ province: place.province, places: [place] })
    }
    return groups
  }, [])

  function selectPlace(id: string) {
    setPlaceId(id)
    if (id !== 'manual') {
      setLongitude('')
      setLatitude('')
    }
  }

  function clearForm(form: HTMLFormElement | null) {
    if (!onClear()) return
    setPlaceId(defaultPlace.id)
    setLongitude('')
    setLatitude('')
    form?.reset()
  }

  return <form className="birth-form" id="birth-form" onSubmit={onSubmit} autoComplete="off" aria-describedby={error ? 'birth-form-error' : undefined}>
    <div className="form-head">
      <span>出生资料</span>
      <span className="privacy-lock"><LockKey size={18} weight="bold" /> 不默认保存</span>
    </div>
    <fieldset className="form-fields" disabled={isSubmitting}>
      <div className="form-grid form-grid-primary">
        <label>出生日期<input name="civilDate" type="date" min="1901-01-01" max="2100-12-31" required defaultValue={initial?.civilDate} /></label>
        <label>出生时间<input name="civilTime" type="time" required defaultValue={initial?.civilTime} /></label>
        <div className="sex-field">
          <span>性别</span>
          <div className="sex-options">
            <label><input name="sexForRule" type="radio" value="male" defaultChecked={initial ? initial.sexForRule === 'male' : true} /><span>男</span></label>
            <label><input name="sexForRule" type="radio" value="female" defaultChecked={initial ? initial.sexForRule === 'female' : false} /><span>女</span></label>
          </div>
        </div>
        <label>出生地
          <span className="select-wrap"><MapPin size={17} weight="fill" /><select name="placePreset" value={placeId} onChange={(event) => selectPlace(event.target.value)}>
            {grouped.map((group) => <optgroup key={group.province} label={group.province}>
              {group.places.map((place) => <option key={place.id} value={place.id}>{place.name}</option>)}
            </optgroup>)}
            <option value="manual">自定义经纬度</option>
          </select></span>
        </label>
      </div>
      {isManual && <div className="form-grid two coordinate-grid">
        <label>经度<input name="longitude" type="number" inputMode="decimal" step="0.00001" min="-180" max="180" value={longitude} onChange={(event) => setLongitude(event.target.value)} required autoFocus /></label>
        <label>纬度<input name="latitude" type="number" inputMode="decimal" step="0.00001" min="-90" max="90" value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></label>
      </div>}
    </fieldset>
    {error && <div className="form-error" id="birth-form-error" role="alert">{error}</div>}
    <button className="submit-button" type="submit" disabled={isSubmitting}>
      {isSubmitting ? <><SpinnerGap className="spin" size={20} /> 正在计算</> : <>{hasChart ? '按新资料重新计算' : '查看今天重点'} <ArrowRight size={20} weight="bold" /></>}
    </button>
    <div className="form-privacy">
      {hasChart && onCancel && <button type="button" className="form-cancel" onClick={onCancel}><XCircle size={15} weight="bold" /> 返回结果</button>}
      <button type="button" onClick={(event) => clearForm(event.currentTarget.form)}>清除当前资料</button>
    </div>
  </form>
}

export function BirthSummary({ summary, theme, onEdit, onClear }: {
  summary: SummaryInput
  theme: ThemeConfig
  onEdit: () => void
  onClear: () => boolean
}) {
  return <div className="birth-summary" role="group" aria-label="当前出生资料">
    <div className="strip-meme" aria-hidden="true"><MemeMedia source={theme.mainMedia} eager /></div>
    <p className="summary-line">
      <strong>{summary.date} · {summary.time}</strong>
      <span>{summary.place}</span>
      <span>{summary.sex}</span>
    </p>
    <div className="summary-actions">
      <button type="button" className="summary-edit" onClick={onEdit}><PencilSimple size={16} weight="bold" /> 修改</button>
      <button type="button" className="summary-clear" aria-label="清除当前资料" onClick={() => onClear()}><Trash size={16} weight="bold" /></button>
    </div>
  </div>
}
