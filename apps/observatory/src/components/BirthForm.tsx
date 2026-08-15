import { useState, type FormEvent } from 'react'
import { ArrowRight, LockKey, MapPin, SlidersHorizontal, SpinnerGap } from '@phosphor-icons/react'
import { birthPlaces, birthPlaceSource } from '../birthPlaces'

const defaultPlace = birthPlaces[0]

export function BirthForm({ isSubmitting, error, onSubmit, onClear, hasChart = false }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
  hasChart?: boolean
}) {
  const [placeId, setPlaceId] = useState(defaultPlace.id)
  const [longitude, setLongitude] = useState(String(defaultPlace.longitude))
  const [latitude, setLatitude] = useState(String(defaultPlace.latitude))

  function selectPlace(id: string) {
    const place = birthPlaces.find((item) => item.id === id)
    setPlaceId(id)
    if (!place) return
    setLongitude(String(place.longitude))
    setLatitude(String(place.latitude))
  }

  function clearForm(form: HTMLFormElement | null) {
    if (!onClear()) return
    setPlaceId(defaultPlace.id)
    setLongitude(String(defaultPlace.longitude))
    setLatitude(String(defaultPlace.latitude))
    form?.reset()
  }

  return <form className={`birth-form ${hasChart ? 'is-compact' : ''}`} id="birth-form" onSubmit={onSubmit} autoComplete="off" aria-describedby={error ? 'birth-form-error' : undefined}>
    <div className="form-head">
      <div><span>出生资料</span><strong>{hasChart ? '更新后重新计算' : '四项填完，先看今日重点'}</strong></div>
      <span className="privacy-lock"><LockKey size={18} weight="bold" /> 不默认保存</span>
    </div>
    <fieldset className="form-fields" disabled={isSubmitting}>
      <div className="form-grid form-grid-primary">
        <label>出生日期<input name="civilDate" type="date" min="1901-01-01" max="2100-12-31" required /></label>
        <label>出生时间<input name="civilTime" type="time" required /></label>
        <div className="sex-field">
          <span>性别（用于排盘规则）</span>
          <div className="sex-options">
            <label><input name="sexForRule" type="radio" value="male" defaultChecked /><span>男</span></label>
            <label><input name="sexForRule" type="radio" value="female" /><span>女</span></label>
          </div>
        </div>
        <label>常用城市
          <span className="select-wrap"><MapPin size={17} weight="fill" /><select name="placePreset" value={placeId} onChange={(event) => selectPlace(event.target.value)}>
            {birthPlaces.map((place) => <option key={place.id} value={place.id}>{place.name}</option>)}
            <option value="manual">手动输入坐标</option>
          </select></span>
        </label>
      </div>
      <details className="advanced-fields">
        <summary><SlidersHorizontal size={17} /> 精确出生位置 <small>临界时刻建议填写</small></summary>
        <p className="coordinate-note">城市选项采用 GeoNames 的 WGS84 代表点，只是近似位置。接近时辰边界时，请在这里输入准确出生地坐标。</p>
        <div className="form-grid two coordinate-grid">
          <label>出生地经度<input name="longitude" type="number" inputMode="decimal" step="0.00001" min="-180" max="180" value={longitude} onChange={(event) => { setPlaceId('manual'); setLongitude(event.target.value) }} required /></label>
          <label>出生地纬度<input name="latitude" type="number" inputMode="decimal" step="0.00001" min="-90" max="90" value={latitude} onChange={(event) => { setPlaceId('manual'); setLatitude(event.target.value) }} required /></label>
        </div>
        <p className="source-attribution">地点数据：<a href={birthPlaceSource.licenseUrl} target="_blank" rel="noreferrer">GeoNames · {birthPlaceSource.license}</a>。真太阳时统一由本地 JPL 星历换算，网页端不接受未经交叉验证的手动结果。</p>
      </details>
    </fieldset>
    {error && <div className="form-error" id="birth-form-error" role="alert">{error}</div>}
    <button className="submit-button" type="submit" disabled={isSubmitting}>
      {isSubmitting ? <><SpinnerGap className="spin" size={20} /> 正在计算</> : <>{hasChart ? '按新资料重新计算' : '查看今天重点'} <ArrowRight size={20} weight="bold" /></>}
    </button>
    <div className="form-privacy">
      <p className="form-footnote">网页端当前支持 1901 至 2100，资料刷新后不保留。</p>
      <button type="button" onClick={(event) => clearForm(event.currentTarget.form)}>清除当前资料</button>
    </div>
  </form>
}
