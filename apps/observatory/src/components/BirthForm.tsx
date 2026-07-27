import type { FormEvent } from 'react'
import { ArrowRight, LockKey, SlidersHorizontal, SpinnerGap } from '@phosphor-icons/react'

export function BirthForm({ isSubmitting, error, onSubmit, onClear }: {
  isSubmitting: boolean
  error: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => boolean
}) {
  return <form className="birth-form" id="birth-form" onSubmit={onSubmit} autoComplete="off" aria-describedby={error ? 'birth-form-error' : undefined}>
    <div className="form-head">
      <div><span>01 / 出生资料</span><strong>认真填，马上排</strong></div>
      <LockKey size={19} weight="bold" aria-label="资料不默认保存" />
    </div>
    <fieldset className="form-fields" disabled={isSubmitting}>
    <div className="form-grid">
      <label>出生日期<input name="civilDate" type="date" min="1849-01-01" max="2150-12-31" required /></label>
      <label>出生时间<input name="civilTime" type="time" required /></label>
      <label>规则性别
        <select name="sexForRule" defaultValue="male">
          <option value="male">男</option>
          <option value="female">女</option>
        </select>
      </label>
      <label>出生地经度<input name="longitude" type="number" inputMode="decimal" step="0.0001" min="-180" max="180" placeholder="例：116.4074" required /></label>
      <label>出生地纬度<input name="latitude" type="number" inputMode="decimal" step="0.0001" min="-90" max="90" placeholder="例：39.9042" required /></label>
    </div>
    <details className="advanced-fields">
      <summary><SlidersHorizontal size={17} /> 高级校正 <small>通常不需要</small></summary>
      <p>系统默认用星历自动换算真太阳时。只有你已有经过校正的时间时，才填写下面两项。</p>
      <div className="form-grid two">
        <label>真太阳日期<input name="apparentDate" type="date" /></label>
        <label>真太阳时间<input name="apparentTime" type="time" /></label>
      </div>
    </details>
    </fieldset>
    {error && <div className="form-error" id="birth-form-error" role="alert">{error}</div>}
    <button className="submit-button" type="submit" disabled={isSubmitting}>
      {isSubmitting ? <><SpinnerGap className="spin" size={20} /> 正在计算</> : <>生成命盘 <ArrowRight size={20} weight="bold" /></>}
    </button>
    <div className="form-privacy">
      <p className="form-footnote">资料仅用于本次计算，不默认保存。</p>
      <button type="button" onClick={(event) => {
        if (onClear()) event.currentTarget.form?.reset()
      }}>清除表单与当前结果</button>
    </div>
  </form>
}
