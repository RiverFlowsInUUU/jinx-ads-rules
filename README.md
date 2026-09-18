# jinx-ads-rules

把 **Jinx**（iOS 去广告 App）的远程黑/白名单，转换成 **mihomo（含 OpenClash）** 与 **Surge** 可直接引用的规则文件。

产出这些文件的转换脚本与完整方法论一并放在 [`skill/`](./skill) 目录，可自行复现（见 §七）。

> ⚠️ **本仓库是格式转换产物，不是原创规则。** 数据全部来自上游仓库 `VME98/jinx-rules`（下称"上游"），本仓库只做**语法翻译**，不新增、不修改任何一条规则内容。

---

## ⚠️ 先读这段：来源与许可

| 项 | 说明 |
|---|---|
| 上游仓库 | <https://github.com/VME98/jinx-rules> |
| 数据版本 | `version.json` → `3.1.9`，`lastUpdate: 2026-09-15T14:35:01Z` |
| 上游许可 | **`license: null`（未声明任何 License）** |
| 本仓库许可 | **同样不主张任何许可**。这是对公开数据的格式翻译，不是我的作品，我不会给它套任何开源协议 |
| 下架承诺 | 上游作者若认为不妥，开 issue 或联系我，**立刻删除本仓库** |
| 再分发建议 | 你要是想用，建议直接引用**上游原始地址**；本仓库只是替你省掉"转换"这一步 |

为什么要写这么重：上游没写 License 的数据，正确做法是**照实标注来源、不据为己有、留好下架通道**，而不是假装它是无主的、更不能套个 MIT 就说是自己的。

---

## 🔴 v2 修正说明（2026-09-19）

**如果你在 2026-09-19 之前引用过本仓库，请务必换成下面的新文件。**

v1 的转换有一个**语义错误**：把 Jinx 的普通域名条目转成了 `DOMAIN,`（**精确匹配**）。但 Jinx 的实际行为是**后缀匹配**——列表里写 `bugly.qq.com`，它会连 `ios.bugly.qq.com` 一起拦。

实测证据（同一份 Jinx 日志，30 条被拦域名）：

| 规则版本 | 覆盖率 | 漏掉的 |
|---|---|---|
| v1（`DOMAIN,` 精确） | 28 / 30 = 93% | `sdkquic.e.qq.com`（靠条目 `e.qq.com`）、`ios.bugly.qq.com`（靠条目 `bugly.qq.com`） |
| **v2（`DOMAIN-SUFFIX,`）** | **30 / 30 = 100%** | 无 |

v2 同时修正了：

1. 普通条目 → `DOMAIN-SUFFIX`（黑名单语义），**不是** `DOMAIN`
2. 白名单 → 保持 `DOMAIN`（**精确**语义）。实测 Jinx 白名单含 `qq.com`，但 `sdk.e.qq.com` 仍被拦 → 白名单**不**向下继承子域。若误用后缀语义，`qq.com` / `baidu.com` / `taobao.com` 会整片放行广告域
3. 3 条混进来的 URL 脏数据（`https://us.l.qq.com/exapp` 等）→ 还原为 host 保留，不再丢弃
4. 差集只剔除被参照规则集**深度覆盖**（后缀/关键词）的条目，不再因为对方有一条精确规则就整条丢掉

**v1 的 `*-domain.list` / `*-domainset.txt` 变体已从仓库移除**（既丢中缀通配，又有精确匹配问题），本仓库只保留下表列出的 v2 文件。

---

## 一、先选文件

**判断标准只有一条：你的客户端里有没有同时跑 `AWAvenue-Ads-Rule`？**

| 你的情况 | mihomo 用 | Surge 用 |
|---|---|---|
| 有 AWAvenue | `mihomo-ads-delta.list` | `surge-ads-delta.list` |
| **没有 / 不确定** | **`mihomo-ads.list`** ⭐ | **`surge-ads.list`** ⭐ |

> 差集只比完整版少 **53 条**（3835 vs 3888），体积差异可以忽略。**除非你确定 AWAvenue 在跑，否则直接用完整版**——省得为 53 条规则埋一个"以为有人管、其实没人管"的坑。

白名单（可选，强烈建议）：

| 文件 | 条数 | 说明 |
|---|---:|---|
| `mihomo-white-guard.list` / `surge-white-guard.list` | 42 | **只要这份**。上游 325 条白名单里，只有 42 条真的会被这套黑名单误杀；其余是上游为**别的**规则集准备的 |

> 别直接引用上游全量 325 条白名单：里面含 `github.com`、`dns.google`、`dropbox.com`、`jsdelivr.net`、`icloud.com`，放在 REJECT 之前会把它们强制直连，国内环境属负优化。

**规则组成**（完整版 3888 条）：

| 类型 | 条数 | 来源 |
|---|---:|---|
| `DOMAIN-SUFFIX` | 3670 | `blacklist.txt` 普通域名 → 后缀语义 |
| `DOMAIN-SUFFIX` | 66 | `blacklist_wildcard.txt` 前缀通配 `*.x.com` |
| `DOMAIN-REGEX` / `DOMAIN-WILDCARD` | 149 | `blacklist_wildcard.txt` 含中缀星号（如 `p*-ad.adkwai.com`） |
| `DOMAIN-SUFFIX` | 3 | 从 URL 脏数据还原的 host |

---

## 二、mihomo / OpenClash 怎么用

```yaml
rule-providers:
  jinx-ads:
    type: http
    behavior: classical          # ⚠️ 必须 classical, 不要用 domain
    format: text
    # 二选一：国内优先 jsDelivr；拉不动 / 被墙时换 raw（注意 raw 在国内常不可达）
    url: "https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-ads.list"
    # url: "https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-ads.list"
    path: ./rule_provider/jinx-ads.list
    interval: 86400

  jinx-white-guard:
    type: http
    behavior: classical
    format: text
    url: "https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-white-guard.list"
    # url: "https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-white-guard.list"
    path: ./rule_provider/jinx-white-guard.list
    interval: 86400

rules:
  # ① 白名单(精确放行)必须在 REJECT 之前
  - RULE-SET,jinx-white-guard,DIRECT
  # ② 广告拦截
  - RULE-SET,jinx-ads,REJECT
  # ③ 你原有的规则接在后面
  # - GEOSITE,cn,DIRECT ...
# ⚠️ REJECT 绝不能排在 GEOSITE,cn,DIRECT / GEOIP,cn,DIRECT 之后 —— 那等于白加
```

> `behavior: domain` 不要用：它对普通域名的匹配范围存在歧义（是否含子域取决于实现），而 `classical` + 显式 `DOMAIN-SUFFIX` 语义明确、可控。

---

## 三、Surge 怎么用

```
[Rule]
# ① 白名单（精确放行）
RULE-SET,https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-white-guard.list,DIRECT
# ② 广告拦截
RULE-SET,https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-ads.list,REJECT,pre-matching,extended-matching
# ③ 你自己的规则接在后面

# —— 备选：jsDelivr 拉不动时，把上面两条换成 raw ——
# RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/surge-white-guard.list,DIRECT
# RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/surge-ads.list,REJECT,pre-matching,extended-matching
```

两个参数的作用：

| 参数 | 作用 |
|---|---|
| `pre-matching` | REJECT 提前到 **DNS / 连接建立**阶段生效，最接近 Jinx 那种系统级 DNS 拦截的体验 |
| `extended-matching` | 额外按 **TLS SNI / HTTP Host** 匹配，**专治 App 直连 IP 导致域名规则失效** |

> **`pre-matching` 只能跟 REJECT 系策略用**，`DIRECT` 加它是无效的（Surge 官方明确）。所以白名单那行不要写它。

---

## 四、为什么"顺序"是生死线

规则引擎**自上而下、先匹配先赢**。你机器上 99% 的国内广告域名，同时也属于「中国大陆域名」。

```
如果顺序是:
    GEOSITE,cn,DIRECT      ← 先命中, 直接放行 ❌
    RULE-SET,jinx-ads,REJECT ← 永远轮不到, 形同虚设

  某个国内 App 的广告域名 = 国内域名 → 被第一条接走 → 直连 → 广告照常显示
```

**判断你顺序对不对的土办法**：开一个本来有广告的 App，看面板的**规则命中**。

- 看到 `jinx-ads` 命中 → 顺序对
- 只看到 `cn` / `DIRECT` / `Final` 命中 → **顺序错了，把 REJECT 提到前面**

---

## 五、已知坑

1. **顺序**：见上一节。这是最常见的"规则看着配了、广告还在"的原因。
2. **超广通配**：源里有 `ad.*`、`ad-*`、`ads-*`、`pangolin*` 这类一条覆盖几百条的规则，拦截面积很大。某 App 出问题先怀疑它们。
3. **中缀星号**：`p*-ad.adkwai.com` 只存在于带类型前缀的格式（mihomo `classical` / Surge `RULE-SET`）。这也是本仓库只提供这两种格式的原因。
4. **jsDelivr 缓存**：更新后 CDN 有几分钟到几小时延迟。急用可在 URL 里加 `?v=<日期>` 绕缓存。
5. **地址二选一**：每个文件都提供 **jsDelivr** 与 **GitHub raw** 两种链接（见文末"文件清单"）。优先用 jsDelivr，理由是 `raw.githubusercontent.com` 在国内常不可达；只有在 jsDelivr 拉不动、或你需要"改动立刻生效"（raw 无 CDN 缓存延迟）时才换 raw，且注意 raw 需能直连 GitHub。
6. **只做域名级拦截**：能拦 DNS 层面的广告域；**同域内嵌广告**（广告和内容同一个域名）需要 MITM/URL 级规则，本仓库的规则**做不到**。
7. **`DOMAIN-SUFFIX` 覆盖面比 `DOMAIN` 大得多**：这是为了复刻 Jinx 的行为。若出现误杀，用白名单加回，而不是把语义改回精确。

---

## 六、数据来源与转换规则

`version.json`（上游 `rules/version.json`）：

```json
{ "version": "3.1.9",
  "lastUpdate": "2026-09-15T14:35:01Z",
  "domainBlacklistCount": 3888,
  "domainWhitelistCount": 325,
  "urlBlacklistCount": 890,
  "urlWhitelistCount": 21,
  "mitmSkipDomainsCount": 33 }
```

语法映射：

| 上游写法 | 含义 | mihomo | Surge |
|---|---|---|---|
| `bugly.qq.com` | 该域名 + **全部子域** | `DOMAIN-SUFFIX,bugly.qq.com` | `DOMAIN-SUFFIX,bugly.qq.com` |
| `*.cupid.iqiyi.com` | 同上（等价） | `DOMAIN-SUFFIX,cupid.iqiyi.com` | `DOMAIN-SUFFIX,cupid.iqiyi.com` |
| `p*-ad.adkwai.com` | 中缀通配（单级） | `DOMAIN-REGEX,^p.*\-ad\.adkwai\.com$` | `DOMAIN-WILDCARD,p*-ad.adkwai.com` |
| 白名单 `qq.com` | **仅精确**，不继承子域 | `DOMAIN,qq.com` | `DOMAIN,qq.com` |

白名单语义的依据：Jinx 日志中白名单含 `qq.com`，但 `sdk.e.qq.com`、`c3.gdt.qq.com`、`ios.bugly.qq.com` 均被正常拦截 → 白名单不向子域继承。

为何用后缀语义的依据：日志中 `sdkquic.e.qq.com` 被拦截，而列表里只有 `e.qq.com`；`ios.bugly.qq.com` 被拦截，而列表里只有 `bugly.qq.com` → 黑名单按后缀生效。

**未转换的内容**：`url_blacklist*`、`url_whitelist*`、`mitm_skip_domains.txt`、`url_response_policies.json` 依赖 MITM 上下文，clash/Surge 的域名规则无法表达，本仓库不提供。

---

## 七、重新生成（脚本随仓库提供）

本仓库的规则**不是手工维护的死快照**——产出它们的脚本与完整方法论一并放在 `skill/` 目录下：

| 路径 | 内容 |
|---|---|
| `skill/SKILL.md` | 完整方法论：匹配语义判定、三平台通配映射表、差集逻辑、白名单瘦身、托管规范、踩坑记录 |
| `skill/scripts/convert_ruleset.py` | 转换主脚本（本仓库 6 个文件全部由它产出） |
| `skill/scripts/upload_to_github.py` | 批量建库/上传辅助脚本（纯 GitHub API，无需 git / gh CLI） |

**① 取源文件**（上游默认分支 `master`，文件在 `rules/` 下）

```bash
mkdir -p jinx-rules && cd jinx-rules
for f in blacklist.txt blacklist_wildcard.txt whitelist.txt whitelist_wildcard.txt version.json; do
  curl -fsSLO "https://raw.githubusercontent.com/VME98/jinx-rules/master/rules/$f"
done
cd ..
```

**② 生成**（六条命令，产出全部 6 个文件）

```bash
SK=skill/scripts/convert_ruleset.py

# 黑名单：完整版（suffix 语义）→ mihomo-ads.list / surge-ads.list
python $SK --src ./jinx-rules --out ./out --fixed blacklist.txt --wild blacklist_wildcard.txt \
    --tag ads --mode suffix --naming repo

# 黑名单：差集版 → mihomo-ads-delta.list / surge-ads-delta.list
python $SK --src ./jinx-rules --out ./out --fixed blacklist.txt --wild blacklist_wildcard.txt \
    --tag ads-delta --mode suffix --naming repo \
    --delta-ref https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml

# 白名单：精简 guard（exact 语义）→ mihomo-white-guard.list / surge-white-guard.list
python $SK --src ./jinx-rules --out ./out --fixed whitelist.txt --wild whitelist_wildcard.txt \
    --tag white-guard --mode exact --naming repo \
    --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt
```

**`--naming repo` 是关键**：让输出文件名与仓库现有文件完全一致（`mihomo-ads.list` / `surge-ads.list`…），可直接覆盖上传，客户端 URL 不用改。省略它则输出社区通用命名 `mihomo-ads-classical.list` / `surge-ads-ruleset.list`。

> ✅ **已实测**：用本节的命令从上游 3.1.9 重跑，产出的 `mihomo-ads.list` / `surge-ads.list` 与仓库现有文件**逐字节一致**（剔除注释行后 `diff` 为空，各 3888 条）。

上游更新后的完整流程就是：重跑 → 覆盖仓库同名文件 → （如删过文件才需要）purge jsDelivr 缓存。

---

## 八、许可与免责

- 规则数据版权归上游 `VME98/jinx-rules` 及其原始来源（多来源合并，不逐一可考）。本仓库**不主张任何权利**、不声明 License。
- **数据与工具分开看**：`skill/` 目录下的转换脚本与方法论文档是本仓库自带的工具，**不含任何上游数据**，可自由取用、修改、再分发；上面"不主张许可"只针对根目录的规则数据，不约束 `skill/`。
- 本仓库仅提供格式转换结果，**不对拦截效果与误杀后果作任何保证**。
- `DOMAIN-SUFFIX` 会拦截整个子域树，请自行评估对自有服务的影响；必要时用白名单放行。
- 若上游作者或任何权利人要求，本仓库将立即删除。

---

## 文件清单

**两种地址前缀，二选一**，拼上文件名即为完整地址：

| 源 | 前缀 | 说明 |
|---|---|---|
| **jsDelivr（推荐）** | `https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/` | 国内可直连、有 CDN 加速；更新后需等缓存刷新 |
| **GitHub raw（备选）** | `https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/` | 内容永远最新、无缓存延迟；但**国内常不可达**，建议配合代理使用 |

例：
- `…/mihomo-ads.list` →
  jsDelivr <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-ads.list> ｜
  raw <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-ads.list>

| 文件 | 条数 | 用途 | 状态 |
|---|---:|---|---|
| `mihomo-ads.list` | 3888 | mihomo `behavior: classical`，完整版 | ⭐ 推荐 |
| `surge-ads.list` | 3888 | Surge `RULE-SET`，完整版 | ⭐ 推荐 |
| `mihomo-ads-delta.list` | 3835 | 已有 AWAvenue 时的差集版 | 可选 |
| `surge-ads-delta.list` | 3835 | 同上，Surge | 可选 |
| `mihomo-white-guard.list` | 42 | mihomo 白名单（精确放行） | ⭐ 建议 |
| `surge-white-guard.list` | 42 | Surge 白名单（精确放行） | ⭐ 建议 |

**完整地址一览**（上排 jsDelivr / 下排 raw，同文件任选其一）：

| 文件 | jsDelivr | raw |
|---|---|---|
| `mihomo-ads.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-ads.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-ads.list> |
| `surge-ads.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-ads.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/surge-ads.list> |
| `mihomo-ads-delta.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-ads-delta.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-ads-delta.list> |
| `surge-ads-delta.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-ads-delta.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/surge-ads-delta.list> |
| `mihomo-white-guard.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-white-guard.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/mihomo-white-guard.list> |
| `surge-white-guard.list` | <https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-white-guard.list> | <https://raw.githubusercontent.com/RiverFlowsInUUU/jinx-ads-rules/main/surge-white-guard.list> |

> **仓库结构**：根目录只保留以上 **6 个规则文件 + `README.md`**；另有 `skill/` 目录（转换脚本 + 方法论文档），**不参与规则引用**，见 §七。
>
> 早期版本的 `*-classical.list`、`*-ruleset.list`、`*-domain.list`、`*-domainset.txt` 等文件**已于 2026-09-19 全部删除**（语义有误或丢失中缀通配）。
> **如果你的客户端仍引用着这些旧地址，请立即换成本表上方的新文件名**——旧地址现已 404，会导致规则集拉取失败。
