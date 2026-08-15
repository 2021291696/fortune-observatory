import { useMemo, useState, type FormEvent } from 'react'
import { ArrowRight, LockKey, MapPin, SpinnerGap } from '@phosphor-icons/react'
import { birthPlaces, type BirthPlace } from '../birthPlaces'

const defaultPlace = birthPlaces[0]

export function BirthForm({ isSubmitting, error, onSubmit, onClear, hasChart = false }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
  hasChart?: boolean
}) {
  const [placeId, setPlaceId] = useState(defaultPlace.id)
  const [longitude, setLongitude] = useState('')
  const [latitude, setLatitude] = useState('')
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

  return <form className={`birth-form ${hasChart ? 'is-compact' : ''}`} id="birth-form" onSubmit={onSubmit} autoComplete="off" aria-describedby={error ? 'birth-form-error' : undefined}>
    <div className="form-head">
      <span>出生资料</span>
      <span className="privacy-lock"><LockKey size={18} weight="bold" /> 不默认保存</span>
    </div>
    <fieldset className="form-fields" disabled={isSubmitting}>
      <div className="form-grid form-grid-primary">
        <label>出生日期<input name="civilDate" type="date" min="1901-01-01" max="2100-12-31" required /></label>
        <label>出生时间<input name="civilTime" type="time" required /></label>
        <div className="sex-field">
          <span>性别</span>
          <div className="sex-options">
            <label><input name="sexForRule" type="radio" value="male" defaultChecked /><span>男</span></label>
            <label><input name="sexForRule" type="radio" value="female" /><span>女</span></label>
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
      <span />
      <button type="button" onClick={(event) => clearForm(event.currentTarget.form)}>清除当前资料</button>
    </div>
  </form>
}
