import { useMemo, useState, type FormEvent } from 'react'
import { ArrowRight, LockKey, MapPin, PencilSimple, SpinnerGap, UserPlus, X } from '@phosphor-icons/react'
import { birthAreas, findArea, findAreaPath } from '../birthPlaces'

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

export function BirthForm({ isSubmitting, error, onSubmit, onClear, initial }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
  initial?: BirthInitial
}) {
  const [provinceCode, setProvinceCode] = useState(() => {
    if (!initial) return birthAreas[0].adcode
    if (initial.placeId === MANUAL) return MANUAL
    return findAreaPath(initial.placeId)[0]?.adcode ?? MANUAL
  })
  const [cityCode, setCityCode] = useState(() => {
    if (!initial || initial.placeId === MANUAL) return ''
    return findAreaPath(initial.placeId)[1]?.adcode ?? ''
  })
  const [districtCode, setDistrictCode] = useState(() => {
    if (!initial || initial.placeId === MANUAL) return ''
    return findAreaPath(initial.placeId)[2]?.adcode ?? ''
  })
  const [longitude, setLongitude] = useState(initial?.longitude ?? '')
  const [latitude, setLatitude] = useState(initial?.latitude ?? '')
  const isManual = provinceCode === MANUAL

  const provinceNode = useMemo(
    () => birthAreas.find((node) => node.adcode === provinceCode) ?? birthAreas[0],
    [provinceCode],
  )
  const cityList = provinceNode.children
  const cityNode = useMemo(
    () => cityList.find((node) => node.adcode === cityCode) ?? cityList[0] ?? null,
    [cityCode, cityList],
  )
  const districtList = cityNode?.children ?? []
  const districtNode = useMemo(
    () => districtList.find((node) => node.adcode === districtCode) ?? districtList[0] ?? null,
    [districtCode, districtList],
  )
  const placeNode = districtNode ?? cityNode ?? provinceNode
  const placeAdcode = isManual ? MANUAL : placeNode?.adcode ?? MANUAL

  function selectProvince(code: string) {
    setProvinceCode(code)
    setCityCode('')
    setDistrictCode('')
    setLongitude('')
    setLatitude('')
  }

  function clearForm(form: HTMLFormElement | null) {
    if (!onClear()) return
    setProvinceCode(birthAreas[0].adcode)
    setCityCode('')
    setDistrictCode('')
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
          <input type="hidden" name="placePreset" value={placeAdcode} />
          <label>省 / 直辖市
            <span className="select-wrap"><MapPin size={17} weight="fill" /><select aria-label="省份" value={provinceCode} onChange={(event) => selectProvince(event.target.value)}>
              {birthAreas.map((node) => <option key={node.adcode} value={node.adcode}>{node.name}</option>)}
              <option value={MANUAL}>自定义经纬度</option>
            </select></span>
          </label>
          {!isManual && cityList.length > 0 && cityNode && <label>市 / 区
            <select aria-label="城市或辖区" value={cityNode.adcode} onChange={(event) => { setCityCode(event.target.value); setDistrictCode('') }}>
              {cityList.map((node) => <option key={node.adcode} value={node.adcode}>{node.name}</option>)}
            </select>
          </label>}
          {!isManual && districtList.length > 0 && districtNode && <label>区 / 县
            <select aria-label="区县" value={districtNode.adcode} onChange={(event) => setDistrictCode(event.target.value)}>
              {districtList.map((node) => <option key={node.adcode} value={node.adcode}>{node.name}</option>)}
            </select>
          </label>}
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
  placeAdcode?: string
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
