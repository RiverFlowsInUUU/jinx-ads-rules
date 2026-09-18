#!/usr/bin/env python3
"""把第三方域名规则源转换为 mihomo / Surge 可用格式。

用法:
  python convert_ruleset.py --src ./jinx-rules --out ./converted \\
      --fixed blacklist.txt --wild blacklist_wildcard.txt --tag ads

  # 与现用规则集做差集(仅当对方"深度覆盖"该条目时才剔除, 见下)
  python convert_ruleset.py ... --delta-ref https://.../AWAvenue-Ads-Rule-Clash-Classical.yaml

  # 白名单瘦身 -- 只保留真正会被黑名单误杀的条目(guard list)
  python convert_ruleset.py --src ./jinx-rules --out ./converted \\
      --fixed whitelist.txt --wild whitelist_wildcard.txt --tag white-guard \\
      --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt

  # 语义开关
  --mode suffix (默认) 普通条目 => DOMAIN-SUFFIX, 复刻 Jinx 等 DNS 过滤器的"域名+全部子域"语义
  --mode exact           普通条目 => DOMAIN, 仅精确匹配

  # 输出命名
  --naming classic (默认)  mihomo-<tag>-classical.list / surge-<tag>-ruleset.list
  --naming repo             mihomo-<tag>.list / surge-<tag>.list
                            (与 jinx-ads-rules 等已托管仓库文件名一致, 可直接覆盖上传)

产出:
  mihomo-<tag>-classical.list   behavior: classical, format: text, 100% 保真
  surge-<tag>-ruleset.list      Surge RULE-SET, 100% 保真

语义要点(踩过的坑, 见 SKILL.md):
  * 黑名单类规则源(Jinx)通常按"域名+子域"拦截, 必须用 --mode suffix。
    用 DOMAIN 精确匹配会漏掉所有未显式列出的子域。
  * 白名单类规则源通常只做精确放行(实测 Jinx: 白名单含 qq.com, 但 sdk.e.qq.com 仍被拦),
    必须用 --mode exact 且放在 REJECT 之前; 若误用 suffix, 会整片放行广告域。
"""
import argparse
import collections
import pathlib
import re
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0'}


def read_text(src):
    if str(src).startswith(('http://', 'https://')):
        return urllib.request.urlopen(
            urllib.request.Request(src, headers=UA), timeout=90).read().decode('utf-8', 'replace')
    return pathlib.Path(src).read_text(encoding='utf-8', errors='replace')


def load_entries(path):
    out = []
    for line in read_text(path).splitlines():
        line = line.strip().lstrip('-').strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        out.append(line)
    return out


def host_of(entry):
    """从 https://host/path?q 里取出 host; 非 URL 返回 None。"""
    m = re.match(r'^https?://([^/?#]+)', entry, re.I)
    return m.group(1).lower().split(':')[0] if m else None


def classify(entry):
    """exact / suffix(*.x) / glob(含中缀星) / url"""
    if '://' in entry:
        return 'url'
    if '*' not in entry and '?' not in entry:
        return 'exact'
    if entry.startswith('*.') and not re.search(r'[*?]', entry[2:]):
        return 'suffix'
    return 'glob'


def glob_to_regex(g):
    return '^' + re.escape(g).replace(r'\*', '.*').replace(r'\?', '.') + '$'


def dedup(seq):
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def parse_reference(ref):
    """解析现用规则集, 返回 (covered_deep, stats)。

    covered_deep(entry): 仅当对方能用 *深度语义*(DOMAIN-SUFFIX / DOMAIN-KEYWORD /
    带通配)覆盖该条目及其子域时才为 True。对方仅用 DOMAIN 精确覆盖时返回 False ——
    因为那样只能挡住该域名本身, 子域仍会漏, 不能作为剔除理由。
    """
    exact, suffix, keyword = set(), set(), set()
    for line in read_text(ref).splitlines():
        line = line.strip().lstrip('-').strip()
        if not line or line.startswith('#') or line.startswith('//') or ',' not in line:
            continue
        parts = [p.strip() for p in line.split(',')]
        rtype, value = parts[0].upper(), parts[1].strip('\'"').lower()
        if rtype == 'DOMAIN':
            exact.add(value)
        elif rtype == 'DOMAIN-SUFFIX':
            suffix.add(value)
        elif rtype == 'DOMAIN-KEYWORD':
            keyword.add(value)
        elif rtype in ('DOMAIN-WILDCARD', 'DOMAIN-REGEX'):
            suffix.add(value)

    def covered_deep(entry):
        e = entry[2:] if entry.startswith('*.') else entry
        if any(e == s or e.endswith('.' + s) for s in suffix):
            return True
        if any(k in e for k in keyword):
            return True
        return False

    return covered_deep, (len(exact), len(suffix), len(keyword))


def build_blacklist_matcher(fixed_paths, wild_paths):
    """构造黑名单碰撞检测器: 判断某白名单条目是否会被这套黑名单误杀。

    命中判定(从严到宽):
      exact  白名单条目 == 黑名单精确条目
      glob   白名单条目被黑名单通配规则匹配 (Jinx 的 * 跨点)
      sub    白名单条目是黑名单精确条目的子域 (黑名单按后缀拦截, 故计入)
    """
    exact, globs = set(), []
    for p in (fixed_paths or []):
        for line in load_entries(p):
            e = line.lstrip('.').lower()
            if '://' not in e and e:
                exact.add(e)
    for p in (wild_paths or []):
        for line in load_entries(p):
            e = line.lstrip('.').lower()
            if '://' not in e and e:
                globs.append((e, re.compile(glob_to_regex(e))))

    def collides(entry):
        e = entry.lstrip('.').lower()
        if e.startswith('*.'):
            e = e[2:]
        if e in exact:
            return 'exact'
        for pat, rx in globs:
            if rx.match(e):
                return 'glob:' + pat
        for b in exact:
            if e.endswith('.' + b):
                return 'sub:' + b
        return None

    return collides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='源目录或文件路径')
    ap.add_argument('--out', required=True, help='输出目录')
    ap.add_argument('--fixed', help='精确域名文件名(在 src 目录下)')
    ap.add_argument('--wild', help='通配域名文件名(在 src 目录下)')
    ap.add_argument('--tag', default='rules', help='输出文件标签, 如 ads / white')
    ap.add_argument('--naming', choices=['classic', 'repo'], default='classic',
                    help='输出命名: classic=mihomo-<tag>-classical.list / surge-<tag>-ruleset.list; '
                         'repo=mihomo-<tag>.list / surge-<tag>.list (与已托管仓库的文件名一致, 便于直接覆盖)')
    ap.add_argument('--mode', choices=['suffix', 'exact'], default='suffix',
                    help='普通条目的匹配语义; 黑名单用 suffix, 白名单用 exact')
    ap.add_argument('--delta-ref', help='现用规则集(URL 或本地路径), 给出则只输出差集')
    ap.add_argument('--guard-against-fixed', nargs='*', help='黑名单精确域名文件, 给出则只保留会被其误杀的白名单条目')
    ap.add_argument('--guard-against-wild', nargs='*', help='黑名单通配域名文件, 同上')
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    entries = []
    for name in [args.fixed, args.wild]:
        if not name:
            continue
        p = src / name if src.is_dir() else pathlib.Path(name)
        entries.extend(load_entries(p))
    entries = dedup(entries)

    if args.guard_against_fixed or args.guard_against_wild:
        def _abs(names):
            if not names:
                return []
            return [str(src / n) if src.is_dir() else n for n in names]
        collides = build_blacklist_matcher(
            _abs(args.guard_against_fixed), _abs(args.guard_against_wild))
        before = len(entries)
        kept = [(e, collides(e)) for e in entries]
        kept = [k for k in kept if k[1]]
        print('guard 模式: %d 条白名单 -> %d 条真正冲突(需保留), 裁掉 %d 条'
              % (before, len(kept), before - len(kept)))
        entries = [k[0] for k in kept]

    if args.delta_ref:
        covered, stat = parse_reference(args.delta_ref)
        print('参照规则集: DOMAIN=%d SUFFIX/通配=%d KEYWORD=%d' % stat)
        before = len(entries)
        entries = [e for e in entries if not covered(e)]
        print('差集(仅剔除被对方深度覆盖的): %d -> %d (-%d)' % (before, len(entries), before - len(entries)))

    counter = collections.Counter()
    mihomo_classical, surge_ruleset = [], []
    recovered = []

    for e in entries:
        kind = classify(e)
        counter[kind] += 1
        if kind == 'url':
            h = host_of(e)
            if h:
                recovered.append(h)
                e, kind = h, 'exact'
            else:
                continue
        if kind == 'exact':
            if args.mode == 'suffix':
                mihomo_classical.append('DOMAIN-SUFFIX,' + e)
                surge_ruleset.append('DOMAIN-SUFFIX,' + e)
            else:
                mihomo_classical.append('DOMAIN,' + e)
                surge_ruleset.append('DOMAIN,' + e)
        elif kind == 'suffix':
            base = e[2:]
            mihomo_classical.append('DOMAIN-SUFFIX,' + base)
            surge_ruleset.append('DOMAIN-SUFFIX,' + base)
        else:
            mihomo_classical.append('DOMAIN-REGEX,' + glob_to_regex(e))
            surge_ruleset.append('DOMAIN-WILDCARD,' + e)

    header = ('# auto-converted by adblock-ruleset-port\n'
              '# source: %s\n# mode: %s\n# entries: %d\n'
              % (args.src, args.mode, len(entries)))
    if args.naming == 'repo':
        names = ('mihomo-%s.list' % args.tag, 'surge-%s.list' % args.tag)
    else:
        names = ('mihomo-%s-classical.list' % args.tag, 'surge-%s-ruleset.list' % args.tag)
    outputs = [
        (names[0], mihomo_classical),
        (names[1], surge_ruleset),
    ]
    for name, lines in outputs:
        (out / name).write_text(header + '\n'.join(lines) + '\n', encoding='utf-8')
        print('  %-32s %6d 行' % (name, len(lines)))

    print('\n分类: exact=%d suffix=%d glob=%d url=%d (其中 %d 条 URL 已还原为 host)'
          % (counter['exact'], counter['suffix'], counter['glob'], counter['url'], len(recovered)))
    print('语义: --mode %s => 普通条目输出为 %s'
          % (args.mode, 'DOMAIN-SUFFIX' if args.mode == 'suffix' else 'DOMAIN'))


if __name__ == '__main__':
    main()
