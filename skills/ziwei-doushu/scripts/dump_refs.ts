/**
 * references 生成器 — 从 vendor/ 数据生成 references/*.md
 *
 * 用法（skill 根目录）: npx tsx scripts/dump_refs.ts
 * 产物：
 *   references/classics.md       — 三本古籍原典全文（骨髓赋/全集/全书精选）
 *   references/patterns.md       — 格局总目录（名称/等级/出处）
 *   references/sihua-tables.md   — 四化表 + 十四主星速查
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
let classicsMd = '# 紫微斗数古籍原典（精选）\n\n';
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

// ─── 2) 格局总目录（从 patterns.ts 源码提取）──────────────────
const patternsSource = fs.readFileSync(path.join(vendorDir, 'patterns.ts'), 'utf-8');
const LEVEL_CN: Record<string, string> = { excellent: '上格', good: '良格', neutral: '中性', caution: '警示' };
const blocks = patternsSource.split('patterns.push({').slice(1);
let patternsMd = '# 紫微斗数格局总目录\n\n';
patternsMd += '> 由 vendor/patterns.ts（detectPatterns）自动提取。排盘时以脚本输出的实际命中为准；\n';
patternsMd += '> 各格局的成立/加分/破格三层条件由引擎逐盘计算，不靠人工口诀判断。\n\n';
for (const block of blocks) {
  const nameMatch = block.match(/name: '([^']+)'/);
  const levelMatch = block.match(/level: (?:breaking[^\n]*\? '([a-z]+)' : [^\n,]+|'([a-z]+)')/);
  const sourceMatch = block.match(/source: '([^']*)'/);
  if (!nameMatch) continue;
  const name = nameMatch[1];
  const level = levelMatch ? (levelMatch[1] ?? levelMatch[2]) : '?';
  const source = sourceMatch ? sourceMatch[1] : '未标注';
  patternsMd += '- **' + name + '**（' + (LEVEL_CN[level] ?? level) + '）— 出处：' + source + '\n';
}
fs.writeFileSync(path.join(refsDir, 'patterns.md'), patternsMd, 'utf-8');
console.log('wrote references/patterns.md');

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
