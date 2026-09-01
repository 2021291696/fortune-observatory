/**
 * references 生成器 — 从 vendor/ 数据生成 references/*.md
 *
 * 用法（skill 根目录）: npx tsx scripts/dump_refs.ts
 * 产物：
 *   references/classics.md       — 三本古籍原典全文（骨髓赋/全集/全书）
 *   references/patterns.md       — 格局全目录（名称/等级/出处/含义/成立·加分·破格）
 *   references/sihua-tables.md   — 四化表 + 十四主星速查
 *
 * 重新生成后无需改 SKILL.md；vendor 更新时重跑本脚本即可同步 references。
 */

import fs from 'node:fs';
import path from 'node:path';
import { guSuiFu } from '../vendor/classics/data/gusuifu';
import { ziWeiQuanJi } from '../vendor/classics/data/quanji';
import { ziWeiQuanShu } from '../vendor/classics/data/quanshu';
import type { Book } from '../vendor/classics/types';
import { SI_HUA_TABLE, STEMS, STAR_DESCRIPTIONS } from '../vendor/constants';

const refsDir = path.join(import.meta.dirname!, '..', 'references');
const vendorDir = path.join(import.meta.dirname!, '..', 'vendor');

fs.mkdirSync(refsDir, { recursive: true });

// ─── 1) 古籍全文 ───────────────────────────────────────────────
const books: Book[] = [guSuiFu, ziWeiQuanJi, ziWeiQuanShu];
let classicsMd = '# 紫微斗数古籍原典（全文）\n\n';
classicsMd += '> 来源：Renhuai123/ziwei-doushu@88194a4（公版古籍整理）。解读引用时标注书名与章节。\n\n';
for (const book of books) {
  classicsMd += '## ' + book.title + '（' + book.dynasty + '·' + book.author + '）\n\n';
  classicsMd += book.intro + '\n\n';
  for (const chapter of book.chapters) {
    classicsMd += '### ' + chapter.title + (chapter.subtitle ? ' — ' + chapter.subtitle : '') + '\n\n';
    for (const p of chapter.paragraphs) {
      classicsMd += '- ' + p.text + '（' + p.id + '）\n';
    }
    classicsMd += '\n';
  }
}
fs.writeFileSync(path.join(refsDir, 'classics.md'), classicsMd, 'utf-8');
console.log('wrote references/classics.md');

// ─── 2) 格局全目录（从 patterns.ts 源码提取）──────────────────
const patternsSource = fs.readFileSync(path.join(vendorDir, 'patterns.ts'), 'utf-8');
const LEVEL_CN: Record<string, string> = { excellent: '上格', good: '良格', neutral: '中性', caution: '警示' };

/**
 * 取一个赋值语句的完整 RHS 文本：从起点扫到深度归零的分号，
 * 容忍多行数组、三目、嵌套括号与字符串内的界符。
 */
function scanStmtRHS(src: string, from: number): string {
  let depth = 0, i = from, quote: string | null = null;
  while (i < src.length) {
    const ch = src[i];
    if (quote) {
      if (ch === '\\') { i += 2; continue; }
      if (ch === quote) quote = null;
    } else if (ch === '\'' || ch === '"' || ch === '`') {
      quote = ch;
    } else if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth--;
    } else if (ch === ';' && depth === 0) {
      return src.slice(from, i);
    }
    i++;
  }
  return src.slice(from);
}

/** 提取文本里全部字符串字面量（单/双引号 + 模板串；模板串三目展开、占位符打平） */
function extractStrings(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(/'([^']*)'|"([^"]*)"|`([^`]*)`/g)) {
    const raw = m[1] ?? m[2] ?? m[3] ?? '';
    const flat = humanizeExpr(raw, '（依盘而定）').trim();
    if (flat) out.push(flat);
  }
  return out;
}

/** 三目双支 ${a ? 'x' : 'y'} → x／y；shaName →（火铃）；其余 ${...} → 占位符 */
function humanizeExpr(s: string, starPh: string): string {
  return s
    .replace(/\$\{shaName\}/g, '（火铃）')
    .replace(/\$\{[^}]*?'([^']+)'\s*:\s*'([^']+)'\s*\}/g, '$1／$2')
    .replace(/\$\{[^}]*\}/g, starPh);
}

/** 取表达式分支部分：带三目时切掉首个 ? 之前的条件，避免条件里的比较字面量混入 */
function branchPart(s: string): string {
  const q = s.indexOf('?');
  return q >= 0 ? s.slice(q + 1) : s;
}

/** name: 表达式 → 可读名。字面量原样；三目取各支以／相连；模板串用{主星}占位 */
function humanizeName(field: string): string {
  const s = field.trim();
  const lit = s.match(/^'([^']+)'$/);
  if (lit) return lit[1];
  if (s.startsWith('`')) return humanizeExpr(s.slice(1, s.lastIndexOf('`')), '{主星}');
  const parts = [...branchPart(s).matchAll(/'([^']*)'/g)].map(t => t[1]).filter(Boolean);
  return parts.length ? parts.join('／') : '{主星}';
}

/** description: 表达式 → 可读文本。模板串展开并占位；三目/纯字符串取引号字面量拼接 */
function humanizeDesc(field: string): string {
  const s = field.trim();
  if (!s) return '';
  if (s.startsWith('`')) {
    let t = humanizeExpr(s.slice(1, s.lastIndexOf('`')), '（主星）');
    t = t.replace(/。?（主星）$/, '');
    return t;
  }
  const parts = [...branchPart(s).matchAll(/'([^']*)'/g)].map(t => t[1]).filter(Boolean);
  return parts.join('；');
}

interface CatalogEntry {
  name: string;
  levels: string[];
  desc: string;
  palaces: string;
  source: string;
  required: string[];
  bonus: string[];
  breaking: string[];
}

const entries: CatalogEntry[] = [];
// 以「/** 注释」和顶层 function 为界切块，保证条件变量与 push 同块
const chunks = patternsSource.split(/\n(?=\/\*\*|\bfunction )/);
for (const chunk of chunks) {
  for (const pm of chunk.matchAll(/patterns\.push\(\{([\s\S]*?)\n\s*\}\);/g)) {
    const body = pm[1];
    const nameField = body.match(/name: (.+),\n/)?.[1];
    if (!nameField) continue;
    const name = humanizeName(nameField);

    const levelExpr = body.match(/level: (.+?),\n/)?.[1] ?? '';
    const levels = [...levelExpr.matchAll(/'([a-z]+)'/g)].map(t => LEVEL_CN[t[1]] ?? t[1]);

    const descField = body.match(/description:([\s\S]*?)\n\s*(?:palaces|conditions|source):/)?.[1] ?? '';
    const desc = humanizeDesc(descField);

    const palRaw = body.match(/palaces: \[([^\]]*)\]/)?.[1] ?? '';
    const palaces = extractStrings(palRaw).join('、');
    const source = body.match(/source: '([^']*)'/)?.[1] ?? '未标注';

    // 条件收集：先取 push 之前同块代码里的变量形式，兜底取 push 体内的内联形式
    const scope = chunk.slice(0, pm.index ?? 0);
    let bonus = [...scope.matchAll(/bonus\.push\('([^']+)'\)/g)].map(t => t[1]);
    let breaking = [...scope.matchAll(/breaking\.push\('([^']+)'\)/g)].map(t => t[1]);

    // required 是 const required = [...] 形式（可能三目/多行），取 push 前最后一次赋值
    let required: string[] = [];
    let lastStart = -1;
    for (const am of scope.matchAll(/const required =/g)) lastStart = am.index ?? -1;
    if (lastStart >= 0) {
      const rhsStart = scope.indexOf('=', lastStart) + 1;
      required = extractStrings(scanStmtRHS(scope, rhsStart));
    }

    // 内联形式：conditions: { required: [...] } 直接写在 push 体内
    const inline = body.match(/conditions: \{([\s\S]*?)\}/)?.[1] ?? '';
    if (!required.length) required = extractStrings(inline.match(/required: \[([^\]]*)\]/)?.[1] ?? '');
    if (!bonus.length) bonus = extractStrings(inline.match(/bonus: \[([^\]]*)\]/)?.[1] ?? '');
    if (!breaking.length) breaking = extractStrings(inline.match(/breaking: \[([^\]]*)\]/)?.[1] ?? '');

    entries.push({ name, levels, desc, palaces, source, required, bonus, breaking });
  }
}

let patternsMd = '# 紫微斗数格局全目录\n\n';
patternsMd += '> 由 vendor/patterns.ts（detectPatterns）自动提取，共 ' + entries.length + ' 格。\n';
patternsMd += '> 排盘时以脚本输出的实际命中为准：引擎逐盘计算成立/加分/破格，本目录供解读时对照含义与条件，不靠人工口诀判断。\n';
patternsMd += '> 等级写作「A→B」表示条件全成时为 A，否则降为 B。\n\n';

patternsMd += '## 速查索引\n\n';
for (const e of entries) {
  patternsMd += '- ' + e.name + '（' + (e.levels.join('/') || '?') + '）\n';
}

patternsMd += '\n## 各格详解\n\n';
for (const e of entries) {
  patternsMd += '### ' + e.name + '（' + (e.levels.join('→') || '?') + '）\n\n';
  patternsMd += '- 出处：' + e.source + '\n';
  if (e.palaces) patternsMd += '- 涉及宫位：' + e.palaces + '\n';
  if (e.desc) patternsMd += '- 含义：' + e.desc + '\n';
  if (e.required.length) patternsMd += '- 成立条件：' + e.required.join('；') + '\n';
  if (e.bonus.length) patternsMd += '- 加分：' + e.bonus.join('；') + '\n';
  if (e.breaking.length) patternsMd += '- 破格警示：' + e.breaking.join('；') + '\n';
  patternsMd += '\n';
}
fs.writeFileSync(path.join(refsDir, 'patterns.md'), patternsMd, 'utf-8');
console.log('wrote references/patterns.md（' + entries.length + ' 格）');

// ─── 3) 四化表 + 主星速查 ─────────────────────────────────────
let tablesMd = '# 四化表与十四主星速查（倪海厦《天纪》口径）\n\n';
tablesMd += '## 十天干四化表（年干 → 禄/权/科/忌）\n\n';
tablesMd += '| 年干 | 化禄 | 化权 | 化科 | 化忌 |\n|---|---|---|---|---|\n';
for (let i = 0; i < 10; i++) {
  const arr = SI_HUA_TABLE[i];
  tablesMd += '| ' + STEMS[i] + ' | ' + arr[0] + ' | ' + arr[1] + ' | ' + arr[2] + ' | ' + arr[3] + ' |\n';
}
tablesMd += '\n> 倪师口径：四化星永远固定不动；大限流年只看走到何处，不改四化。\n\n';
tablesMd += '## 十四主星速查\n\n| 主星 | 关键词 | 星性 | 五行 |\n|---|---|---|---|\n';
for (const [name, desc] of Object.entries(STAR_DESCRIPTIONS)) {
  tablesMd += '| ' + name + ' | ' + desc.keywords + ' | ' + desc.nature + ' | ' + desc.element + ' |\n';
}
fs.writeFileSync(path.join(refsDir, 'sihua-tables.md'), tablesMd, 'utf-8');
console.log('wrote references/sihua-tables.md');
