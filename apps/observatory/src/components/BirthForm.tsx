import { useMemo, useState, type FormEvent } from 'react'
import { ArrowRight, LockKey, MapPin, PencilSimple, SpinnerGap, UserPlus, X } from '@phosphor-icons/react'
import { birthPlaces, birthPlaceProvinces } from '../birthPlaces'

const defaultPlace = birthPlaces[0]
const MANUAL = 'manual'

export type BirthInitial = {
  name: string
  civilDate: string
  civilTime: string
  sexForRule: string
  placeId: string
  longitude: string
  latitude: string
}

function initialProvince(initial?: BirthInitial): string {
  if (!initial) return defaultPlace.province
  if (initial.placeId === MANUAL) return MANUAL
  return birthPlaces.find((place) => place.id === initial.placeId)?.province ?? defaultPlace.province
}

export function BirthForm({ isSubmitting, error, onSubmit, onClear, initial }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
  initial?: BirthInitial
}) {
  const [province, setProvince] = useState(() => initialProvince(initial))
  const provincePlaces = useMemo(() => birthPlaces.filter((place) => place.province === province), [province])
  const [placeId, setPlaceId] = useState(initial?.placeId ?? defaultPlace.id)
  const [longitude, setLongitude] = useState(initial?.longitude ?? '')
  const [latitude, setLatitude] = useState(initial?.latitude ?? '')
  const isManual = province === MANUAL

  function selectProvince(next: string) {
    setProvince(next)
    setLongitude('')
    setLatitude('')
    if (next === MANUAL) {
      setPlaceId(MANUAL)
      return
    }
    setPlaceId(birthPlaces.find((place) => place.province === next)?.id ?? MANUAL)
  }

  function selectPlace(id: string) {
    setPlaceId(id)
    setLongitude('')
    setLatitude('')
  }

  function clearForm(form: HTMLFormElement | null) {
    if (!onClear()) return
    setProvince(defaultPlace.province)
    setPlaceId(defaultPlace.id)
    setLongitude('')
    setLatitude('')
    form?.reset()
  }

  return <form className="birth-form" id="birth-form" onSubmit={onSubmit} autoComplete="off" aria-describedby={error ? 'birth-form-error' : undefined}>
    <div className="form-head">
      <span>出生资料</span>
      <span className="privacy-lock"><LockKey size={18} weight="bold" /> 只存本机</span>
    </div>
    <fieldset className="form-fields" disabled={isSubmitting}>
      <div className="form-grid form-grid-primary">
        <label>备注名<input name="displayName" type="text" maxLength={12} placeholder="我" defaultValue={initial?.name} required /></label>
        <div className="sex-field">
          <span>性别</span>
          <div className="sex-options">
            <label><input name="sexForRule" type="radio" value="male" defaultChecked={initial ? initial.sexForRule === 'male' : true} /><span>男</span></label>
            <label><input name="sexForRule" type="radio" value="female" defaultChecked={initial ? initial.sexForRule === 'female' : false} /><span>女</span></label>
          </div>
        </div>
        <label>出生日期<input name="civilDate" type="date" min="1901-01-01" max="2100-12-31" required defaultValue={initial?.civilDate} /></label>
        <label>出生时间<input name="civilTime" type="time" required defaultValue={initial?.civilTime} /></label>
        <div className="place-field" role="group" aria-label="出生地">
          <label>省 / 直辖市
            <span className="select-wrap"><MapPin size={17} weight="fill" /><select name="province" value={province} onChange={(event) => selectProvince(event.target.value)}>
              {birthPlaceProvinces.map((name) => <option key={name} value={name}>{name}</option>)}
              <option value={MANUAL}>自定义经纬度</option>
            </select></span>
          </label>
          <label>市 / 县
            <select name="placePreset" value={isManual ? '' : placeId} disabled={isManual} onChange={(event) => selectPlace(event.target.value)}>
              {isManual && <option value="">已选自定义经纬度</option>}
              {provincePlaces.map((place) => <option key={place.id} value={place.id}>{place.name}</option>)}
            </select>
          </label>
        </div>
      </div>
      {isManual && <div className="form-grid two coordinate-grid">
        <label>经度<input name="longitude" type="number" inputMode="decimal" step="0.00001" min="-180" max="180" value={longitude} onChange={(event) => setLongitude(event.target.value)} required autoFocus /></label>
        <label>纬度<input name="latitude" type="number" inputMode="decimal" step="0.00001" min="-90" max="90" value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></label>
      </div>}
    </fieldset>
    {error && <div className="form-error" id="birth-form-error" role="alert">{error}</div>}
    <button className="submit-button" type="submit" disabled={isSubmitting}>
      {isSubmitting ? <><SpinnerGap className="spin" size={20} /> 正在计算</> : <>{initial ? '保存并重新计算' : '排盘并看运势'} <ArrowRight size={20} weight="bold" /></>}
    </button>
    <div className="form-privacy">
      <span className="form-footnote">资料只保存在这台设备上，不上传服务器。</span>
      <button type="button" onClick={(event) => clearForm(event.currentTarget.form)}>清空重填</button>
    </div>
  </form>
}

export type StoredUser = {
  id: string
  name: string
  createdAt: string
  birth: {
    civil_datetime: string
    timezone_id: 'Asia/Shanghai'
    longitude: number
    latitude: number
    sex_for_rule: string
    use_apparent_solar_time: true
  }
}

export function UserBar({ users, currentId, editingId, manage = false, onSwitch, onStartAdd, onRename, onRemove }: {
  users: StoredUser[]
  currentId: string | null
  editingId: string | null
  manage?: boolean
  onSwitch: (id: string) => void
  onStartAdd?: () => void
  onRename?: (id: string, name: string) => void
  onRemove?: (id: string) => void
}) {
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [draftName, setDraftName] = useState('')

  function commitRename(id: string) {
    const name = draftName.trim().slice(0, 12)
    if (name && onRename) onRename(id, name)
    setRenamingId(null)
  }

  return <div className="user-bar" role="group" aria-label="命盘用户">
    {users.map((user, index) => <div
      key={user.id}
      className={`user-chip ${user.id === currentId ? 'is-current' : ''} ${user.id === editingId ? 'is-editing' : ''}`}
    >
      {renamingId === user.id
        ? <input
            className="user-rename"
            value={draftName}
            maxLength={12}
            autoFocus
            aria-label={`重命名 ${user.name}`}
            onChange={(event) => setDraftName(event.target.value)}
            onBlur={() => commitRename(user.id)}
            onKeyDown={(event) => { if (event.key === 'Enter') commitRename(user.id); if (event.key === 'Escape') setRenamingId(null) }}
          />
        : <button type="button" className="user-pick" onClick={() => onSwitch(user.id)} title={`切换到 ${user.name}`}>
          {user.name}{index === 0 && <span className="user-default" title="默认用户">★</span>}
        </button>}
      {manage && renamingId !== user.id && <>
        <button type="button" className="user-act" aria-label={`重命名 ${user.name}`} title="重命名"
          onClick={() => { setRenamingId(user.id); setDraftName(user.name) }}><PencilSimple size={14} weight="bold" /></button>
        <button type="button" className="user-act user-remove" aria-label={`删除 ${user.name}`} title="删除此用户"
          onClick={() => onRemove?.(user.id)}><X size={14} weight="bold" /></button>
      </>}
    </div>)}
    {onStartAdd && <button type="button" className="user-chip user-chip-add" onClick={onStartAdd}>
      <UserPlus size={16} weight="bold" /> 新用户
    </button>}
  </div>
}
