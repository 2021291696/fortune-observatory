"""解说话术语料库（lore）— 口径以三端命理 skill 的 references 原文为准。

两层结构：
- 导航层：从 skill 知识体系提炼的解读框架（本文件手写块），告诉模型按什么顺序组织分析；
- 断语层：skills/bazi/references 与 skills/ziwei-doushu/references 的原文整包注入，
  断语内容以原文为准——该说什么就说什么，原文没有的不得编造出处。

排盘事实仍以服务端签名 facts 为准，lore 不参与任何计算。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

GENERAL_STYLE_GUIDE = (
    "【专业断语风格】在遵守上述全部禁令的前提下：优先输出有信息量的传统命理断语，"
    "而不是安慰性的泛泛之谈。每个判断必须锚定 facts 中的具体宫位、干支、星曜、四化或大限，"
    "关键断语用括号标注传统出处（如《紫微斗数全书·四化论》《骨髓赋》《穷通宝典》）。"
    "术语第一次出现时仍需一句白话解释。facts 中没有的星曜、宫位、干支不得虚构。"
)

ZIWEI_LORE = """【紫微斗数解读框架】按此顺序组织分析：
1. 命格总纲：命宫主星定性格底色（星性+亮度），身宫定中年后归向；引用《骨髓赋·总论篇》"命宫主星定其格局，三方四正定其用武"。
2. 四化论断（核心）：化禄主财、主缘、主能力变现；化权主权、主决断、主独当一面；化科主名、主贵人、主文书；化忌主病、主煞、主深刻功课。四化落在哪个宫，那个领域就是人生的课题或资源所在（《全书·四化论》："四化所在宫位，决定一生重大事件之节点"）。
3. 三方四正：命宫+财帛+官禄+迁移互照，构成用武之地；对宫互为表里。
4. 大限节奏：当前大限宫位为十年主旋律，流年为一年之目。

【十四主星速断】（庙旺全力、平和、落陷减力但不改星性）
- 紫微：帝座，尊贵领导；得左辅右弼为"君臣庆会"，孤坐无辅为孤君，纵贵不久（《全书》）。化权主独断，化科主名。
- 天机：智慧机变善谋，宜策划咨询文教；忌善变无主，得昌曲成器。
- 太阳：化贵，主名声公务男性亲人；庙旺贵显，落陷劳而无获、多为他人作嫁。
- 武曲：财星，刚毅果决善理财；化禄正财丰厚，化忌主财劫、须防金属意外与孤决。
- 天同：福德星，温和享福随缘；化禄福气加厚，煞会同宫反主安逸误事。
- 廉贞：次桃花化囚，才艺与原则感并存；化忌主血光官非感情纠缠（《全书》）。
- 天府：禄库之星，稳重保守善积蓄，主衣食无忧；喜见禄存。
- 太阴：田宅主，柔美细腻；庙旺主不动产富贵，落陷主暗耗劳心；女命太阴庙旺尤吉。
- 贪狼：欲望桃花多才，社交应酬强；遇火星或铃星为"火贪/铃贪"横发格，忌空劫则华而不实。
- 巨门：化暗，口舌是非亦是口才；化禄"以口生财"宜律师教师传媒，化忌防口舌官非。
- 天相：化印，辅佐行政忠厚；喜会紫微廉贞借威成事，遇刑忌夹制则印绶失力。
- 天梁：化荫，长辈星庇护星，宜医疗法律教育；化科主名声，化禄反主虚名浮禄。
- 七杀：将星，果决孤克，宜武职开拓创业；"七杀朝斗"爵禄荣昌，逢空劫主漂泊。
- 破军：化耗，开创变动，先散后聚破而后立；宜技术专长立身，忌安于现状。

【四化落宫速断】命宫=自身课题；兄弟=同辈合伙人；夫妻=婚姻；子女=晚辈作品；财帛=现金流；疾厄=身体；迁移=外出机遇；交友=人脉圈层；官禄=事业；田宅=家宅财库；福德=精神享受；父母=长辈文书。
【宫位规则】空宫借对宫主星论（需说明是借宫）；主星落陷按减力解读并给建设性方向（"落陷之人有'不甘'二字推动，反能大成"——《全书·命宫》）。"""

BAZI_LORE = """【八字解读框架】按此顺序组织分析：
1. 日主旺衰：看日干得令（月支）、得地（坐支通根）、得势（同党多寡）定身旺身弱。
2. 十神格局：月令透干定格局，用神相神有力无力定格局高低（《子平真诠》）。
3. 喜用忌仇：身弱喜印比（生扶），身旺喜官杀（克）、食伤（泄）、财（耗）；调候参考《穷通宝典》寒暖燥湿。
4. 大运流年：大运为纲（十年主旋律，天干管前五年、地支管后五年），流年为目（当年应期）。

【十神心性速断】
- 正官：规矩约束，贵气官声，守成自律。七杀：魄力胆识，压力竞争，开拓敢闯。
- 正财：正当收入，务实节俭。偏财：流动之财，人缘机遇，慷慨社交。
- 正印：庇护学识，名誉靠山。偏印：直觉悟性，另类专才，多思少断。
- 食神：才艺口福，温和表达。伤官：才华外露，傲气叛逆，敢言敢破。
- 比肩：自我同辈，合伙分力。劫财：竞争争夺，破财亦能劫煞为权。

【断语要点】十神落在年月日时柱各有领域（年=祖上早年、月=父母青年、日=自身婚姻、时=子女晚景）；干支生克冲合定顺逆；引断时标注出处，术语配白话。"""

QIZHENG_LORE = """【七政四余解读框架】
1. 昼夜盘：昼生重太阳、夜生重太阴（《果老星宗》口径），先定命盘基调。
2. 命主与身主：命主星（命宫支守护星）定一生体面所在，身主星定身心所系；二星得地则体用兼备。
3. 庙旺：居垣（星躔本命宫）最有力，升殿（躔本属宿）次之；失地星曜按减力论。
4. 恩难仇用：恩星=生我助力（贵人资源），难星=克我压力（课题磨砺），用星=我克可控（可驾驭的财与事），仇星=我生泄耗（消耗付出）。难星重不写凶，写"以磨砺换深度"。
5. 洞微大限：行限宫位定当前十年舞台，结合限主星断运段主题。"""

FORTUNE_LORE = """【运势断法框架】
1. 先纲后目：当前大限（十年）定主题基调，流年（一年）定具体应期；流年干支与大限、原局发生刑冲合会、引动四化处为事件触发点。
2. 节奏语言：用"那十年容易/这十年会容易/今年注意"表达节奏与坑，不写已然的履历式断语。
3. 应期提示：流年引动财帛/官禄/夫妻等宫时，该领域才有明确动静；未引动的领域如实说"平缓"。
4. 断语落点：给出该阶段可执行的一两个具体动作（防守型或进攻型），并说明依据的盘面事实。"""

_LORE_BY_BUNDLE: dict[str, str] = {
    "ziwei.chart": ZIWEI_LORE,
    "qizheng.chart": QIZHENG_LORE,
    "fortune.daily": FORTUNE_LORE,
    "fortune.period": FORTUNE_LORE,
    "fortune.window": FORTUNE_LORE,
    "domain.health": ZIWEI_LORE,
    "domain.relationship": ZIWEI_LORE,
    "domain.career": ZIWEI_LORE,
    "domain.wealth": ZIWEI_LORE,
}


# ---- 断语层：skill references 原文整包 ----

_API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _API_DIR.parents[1]

# (标题, 相对路径)；单文件超限时截断保护预算
_SKILL_SOURCES: tuple[tuple[str, str], ...] = (
    ("紫微斗数·典籍断语（骨髓赋/全书/全集）", "skills/ziwei-doushu/references/classics.md"),
    ("紫微斗数·格局", "skills/ziwei-doushu/references/patterns.md"),
    ("紫微斗数·四化表（倪海厦《天纪》口径）", "skills/ziwei-doushu/references/sihua-tables.md"),
    ("八字·典籍摘要（穷通宝典/子平真诠）", "skills/bazi/references/classical-texts.md"),
    ("八字·大运流年规则", "skills/bazi/references/dayun-rules.md"),
    ("八字·五行生克表", "skills/bazi/references/wuxing-tables.md"),
    ("八字·神煞表", "skills/bazi/references/shensha-table.md"),
    ("八字·时辰表", "skills/bazi/references/shichen-table.md"),
)
_PER_FILE_CAP = 20000


@lru_cache(maxsize=1)
def skill_canon() -> str:
    """skill references 原文整包；文件缺失时跳过该份，不阻断解读。"""
    parts: list[str] = []
    for title, rel in _SKILL_SOURCES:
        try:
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        if text.strip():
            parts.append(f"≪{title}》\n{text[:_PER_FILE_CAP]}")
    return "\n\n".join(parts)


_SKILL_RULE = (
    "【skill 口径原文使用铁律】下方≪》标注的原文是断语的唯一权威来源："
    "1. 涉及星曜、四化、宫位、十神、大运流年的判断，优先转述原文中对应的断语——该说什么就说什么，不要改成安慰性的泛泛之谈；"
    "2. 原文断语与本框架冲突时，以原文为准；"
    "3. 原文没有覆盖的组合，按框架推导并明确说'原文未直接论及，按通则推'，禁止编造原文没有的引文或出处；"
    "4. facts 与原文冲突时（如原文说庙旺、facts 说落陷），以 facts 为准。"
)


def lore_for_bundle_types(bundle_types: set[str]) -> str:
    """导航框架 + skill 口径原文整包 + 风格指南；组合包取首个命中框架。"""
    canon = skill_canon()
    skill_block = f"{_SKILL_RULE}\n\n{canon}" if canon else ""
    for bundle_type in (
        "ziwei.chart",
        "qizheng.chart",
        "fortune.daily",
        "fortune.period",
        "fortune.window",
    ):
        if bundle_type in bundle_types:
            return _LORE_BY_BUNDLE[bundle_type] + "\n\n" + skill_block + "\n\n" + GENERAL_STYLE_GUIDE
    for bundle_type in ("domain.health", "domain.relationship", "domain.career", "domain.wealth"):
        if bundle_type in bundle_types:
            return _LORE_BY_BUNDLE[bundle_type] + "\n\n" + skill_block + "\n\n" + GENERAL_STYLE_GUIDE
    return GENERAL_STYLE_GUIDE + ("\n\n" + skill_block if skill_block else "")
