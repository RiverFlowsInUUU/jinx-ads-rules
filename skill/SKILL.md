---
name: adblock-ruleset-port
description: 把第三方广告/域名规则源（Jinx、AdGuard、anti-AD、GOODBYEADS 等）转换并移植到 mihomo(OpenClash) / Surge / QuantumultX，含通配语义映射、覆盖度差集、白名单瘦身(guard list)、引用配置写法与规则顺序陷阱、规则仓库托管与 README 交付规范。触发词：规则集移植、黑名单转 clash、广告规则转 surge、jinx 规则、DOMAIN-WILDCARD、rule-provider behavior、去广告规则引用、AWAvenue、白名单瘦身、规则仓库 readme。
agent_created: true
---

# 广告 / 域名规则集跨平台移植

## 适用

把一个平台的域名黑/白名单，转换成另一个平台能吃的格式并接入。

典型场景：某 App 的广告只有 Jinx（iOS 系统级 DNS 拦截）拦得住，AWAvenue-Ads 拦不住 → 把 Jinx 的黑名单补进 mihomo / Surge。

## 铁律

1. **先量化再动手**：不要假设"规则没生效"，先做**覆盖度差集**（源列表 vs 现用列表）。实测中 AWAvenue-Ads 只覆盖 Jinx 黑名单的 22.5%——问题是"域名不全"，不是"规则没生效"。这两者的修法完全不同。
2. **先测匹配语义，再动手转换**（最易错、代价最大，见下节）。黑名单一般按"域名 + 全部子域"拦截，白名单一般只做精确放行。**默认假设"普通条目 = 精确匹配"会导致大面积漏拦。**
3. **通配语义不可想当然**：三个平台的 `*` 含义不同，直接复制文件必然出错（见下表）。
4. **规则顺序是生死线**：REJECT 规则集必须排在 `DIRECT` / `GEOSITE,cn,DIRECT` **之前**，否则永远轮不到。
5. **别用高性能格式装通配**：`behavior: domain` 和 Surge `DOMAIN-SET` 都装不下中缀星号，且普通条目的子域语义有歧义。要 100% 保真只能用 `classical` / `RULE-SET`。
6. 改设备配置走各自 SOP（OpenClash 见 `openclash-config-change` skill；Surge 见 `surge-profile-optimize` skill），先只读诊断、备份、校验、用户确认。
7. **白名单要瘦身再上**，别整份前插（见"白名单瘦身"节）。托管成公开仓库时必须写 README（见"对外交付"节）并保留上游来源声明。

## 第一步：实测匹配语义（不可跳过）

**黑名单与白名单的语义常常不同，必须分别实测。** 做法：拿客户端日志里真实的 `blocked` / `allowed` 域名，回溯它在源列表里"靠哪条规则被覆盖"。三种关系：`exact`（域名本身在列表里）、`glob`（被通配规则匹配）、`suffix`（只有某个**祖先域**在列表里）。

| 判据 | 结论 |
|---|---|
| 出现 `suffix` 命中（子域被拦、列表里只有父域） | 黑名单是**后缀语义** → 用 `DOMAIN-SUFFIX` |
| `allowed` 域名里存在黑名单后缀祖先 | 黑名单是**精确语义** → 用 `DOMAIN` |
| 白名单含 `qq.com`，但 `sdk.e.qq.com` 仍被拦 | 白名单是**精确语义**，不继承子域 → 用 `DOMAIN` |

实例（Jinx，2026-09-19）：日志中 `sdkquic.e.qq.com` 被拦而列表里只有 `e.qq.com`；`ios.bugly.qq.com` 被拦而列表里只有 `bugly.qq.com` → 黑名单 = 后缀语义。同时白名单含 `qq.com`、`baidu.com`、`taobao.com`，但 `sdk.e.qq.com` / `c3.gdt.qq.com` / `ios.bugly.qq.com` 均被正常拦截 → 白名单 = 精确语义。

**黑白名单语义搞反的后果都是灾难性的**：黑名单用精确 → 子域全漏（日志覆盖率 28/30 → 30/30，即那 7% 全部漏掉）；白名单用后缀 → `qq.com` 一条就把 `bugly.qq.com` / `gdt.qq.com` / `e.qq.com` 下的广告全部放行。

## 通配语义映射表（核心知识）

| 源写法 | mihomo | Surge | 说明 |
|---|---|---|---|
| `x.com`（黑名单） | **`DOMAIN-SUFFIX,x.com`** | **`DOMAIN-SUFFIX,x.com`** | 后缀语义：域名 + 全部子域 |
| `x.com`（白名单） | `DOMAIN,x.com` | `DOMAIN,x.com` | 精确语义：仅该域名本身 |
| `*.x.com` | **`DOMAIN-SUFFIX,x.com`** 或 `+.x.com` | `DOMAIN-WILDCARD,*.x.com` 或 `DOMAIN-SUFFIX,x.com` | ⚠️ mihomo 的 `*.x.com` **只匹配一级且不跨点**，直接用会漏多级子域 |
| `p*-ad.x.com` | **`DOMAIN-REGEX,^p.*-ad\.x\.com$`** | `DOMAIN-WILDCARD,p*-ad.x.com` | mihomo **不支持星号内嵌** |
| `.x.com` | `.x.com`（多级子域，不含裸域） | — | mihomo 专有 |
| `+.x.com` | `+.x.com`（多级子域 **含**裸域） | — | mihomo 专有 |

**官方依据**
- mihomo（`wiki.metacubex.one/handbook/syntax/`，域名通配符章节）：`*` 一次只匹配一级；`+` / `.` 可匹配多级但只能作前缀；含裸域用 `+.x`。**与 `DOMAIN-WILDCARD` 不是同一套语法。**
- Surge（`manual.nssurge.com/rules/domain.html`）：`*` 匹配任意字符**且跨点**（`*.example.com` 匹配 `a.b.example.com`）、`?` 匹配一个字符、支持 `[...]` 字符类 → **与通用 glob 等价**。
- Surge `DOMAIN-SET`：一行一条，裸域名 = DOMAIN，`.x.com` = DOMAIN-SUFFIX，**不支持 `*`**，上限 100 万条，性能优于 RULE-SET。

**转换总原则**：黑名单按**跨级放宽**（mihomo 用 `DOMAIN-SUFFIX` / `+.`），宁多拦勿漏拦；白名单反之要谨慎。

## 转换步骤

用 `scripts/convert_ruleset.py`：

```bash
# 黑名单：--mode suffix（默认）
python convert_ruleset.py --src <源目录> --out <输出目录> \
    --fixed blacklist.txt --wild blacklist_wildcard.txt --tag ads --mode suffix
```

产出 2 个文件（完整版）：

| 文件 | 用途 |
|---|---|
| `mihomo-<tag>-classical.list` | mihomo `behavior: classical` + `format: text`，**100% 保真** |
| `surge-<tag>-ruleset.list` | Surge RULE-SET，**100% 保真** |

**`--naming repo`（托管场景务必加）**：输出改为 `mihomo-<tag>.list` / `surge-<tag>.list`，即**与仓库现有文件名一致**，可直接覆盖上传、客户端 URL 一个字都不用改。不加则用上表的社区通用命名。

> 命名对照（`--tag` 用 `ads` / `ads-delta` / `white-guard` 时）：`--naming repo` 产出的正是 `mihomo-ads.list`、`surge-ads-delta.list`、`mihomo-white-guard.list` 这类托管常用名。

> 不再输出 `behavior: domain` / Surge `DOMAIN-SET` 变体：这两者既装不下中缀通配，普通条目的子域语义又依赖实现细节。3.9k 条量级下 RULE-SET 的性能损失可忽略。

**再算差集**（用户已有其他广告列表时做，避免重复加载）。

⚠️ **差集只能剔除被对方「深度覆盖」的条目**——即对方必须有 `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD` / 通配规则。**对方只有一条 `DOMAIN,` 精确规则不足以作为删除理由**，否则会漏掉该域名的子域。

实测教训：AWAvenue `Clash-Classical` 949 条里 **936 条是 `DOMAIN,` 精确**、仅 12 条 SUFFIX。v1 按"精确命中即已覆盖"删掉了 874 条；改成"深度覆盖才算"后只该删 **53 条**。差集省下的量远小于风险，**不确定客户端是否真的加载了参照列表时，直接给完整版。**

## 自定义追加（`--extra`）—— 上游没有、但你要拦的域名

**动机**：上游规则集总有收录缺口（实测：相机 App 冷启动时 `msg.qy.net` 放行，广告素材照常渲染）。补规则时如果直接手改 `mihomo-*.list`，**下次从上游重跑就被完全覆盖**，而且不会有任何提示。

做法：把追加域名单独放一个文件（托管仓库里叫 `custom-ads.list`），生成时用 `--extra` 并进去：

```bash
python convert_ruleset.py --src <源目录> --out <输出目录> \
    --fixed blacklist.txt --wild blacklist_wildcard.txt --tag ads --mode suffix --naming repo \
    --extra ./custom-ads.list          # ← 差集版那条命令也要带
```

语义与位置约定：

| 项 | 行为 |
|---|---|
| 合并时机 | **条目池构建之后、guard / `--delta-ref` 过滤之前** → 追加项与上游条目同等对待 |
| 落点 | 输出**末尾**（`entries + added` 的 dedup 顺序），便于 diff 核验 |
| 表头 | 多一行 `# extra: custom-ads.list(N)`，N = 该文件读入条数 |
| 路径解析 | 先按 cwd 找；找不到再按 `--src` 目录找（`--extra custom-ads.list` 与 `--extra ./custom-ads.list` 都可用） |
| 语义 | 普通域名 → `DOMAIN-SUFFIX`（该域 + 全部子域），与黑名单一致 |

**验收判据（必做，防止静默漂移）**：重新生成后与线上文件对 diff，**只允许三处变化** —— 表头 `# entries` 数字、多一行 `# extra:`、末尾按顺序多出 N 条；其余正文**逐行不变**。

⚠️ **别因为"追加快、不用改配置"就滥用**：只加**被第三方权威名单收录**的域名。判定方式见 skill `openclash-config-change` 的 `scripts/scan_leaks.py`。
⚠️ `--extra` 是 `nargs='*'`：**必须放在命令末尾**，或后面紧跟另一个 `--选项`；否则会把后面的位置参数当成文件名吞掉。

## 引用配置

**mihomo / OpenClash**

```yaml
rule-providers:
  jinx-ads:
    type: file            # 或 http
    behavior: classical
    format: text
    path: ./rule_provider/jinx-ads.list
    interval: 86400

rules:
  - RULE-SET,jinx-white-guard,DIRECT   # 白名单(精确放行)在前
  - RULE-SET,jinx-ads,REJECT           # ⚠️ 必须在 DIRECT/GEOSITE,cn 之前
```

规则集文件放 `/etc/openclash/rule_provider/`。

**Surge**

```
[Rule]
RULE-SET,https://host/surge-white-guard.list,DIRECT
RULE-SET,https://host/surge-ads.list,REJECT,pre-matching,extended-matching
```

| 参数 | 作用 |
|---|---|
| `pre-matching` | REJECT 提前到 **DNS / TCP 握手**阶段生效（最接近系统级 DNS 拦截的体验） |
| `extended-matching` | 额外用 TLS SNI / HTTP Host 匹配，**解决 App 直连 IP 导致域名规则失效** |

**Surge 参数两条硬约束**（官方文档原文，易踩）：
1. `pre-matching` **只支持 REJECT 系策略**——写在 `DIRECT` 行上无意义（白名单行不要加）。
2. `pre-matching` **不能出现在规则集文件内部**，只能写在 profile 的 `RULE-SET` 行上；文件内出现会被当无效行跳过。规则集文件内部**允许**逐行写 `no-resolve` / `extended-matching`。

## 白名单瘦身（guard list）—— 强烈建议

**不要把上游白名单整份插到最前面走 DIRECT。** 白名单通常混着大量"为其他规则集准备的"域名（实测 Jinx 325 条里含 `github.com` / `dns.google` / `jsdelivr.net` / `dropbox.com` / `onedrive.live.com` / `icloud.com`）。整份前插 = 把这些域名全部**强制直连**，在国内网络环境下是负优化。

只保留**会被当前黑名单误杀**的条目。碰撞判定三种关系：`exact`（等于黑名单精确条目）、`glob`（被黑名单通配规则匹配）、`sub`（是黑名单精确条目的子域）。

```bash
python convert_ruleset.py --src <源目录> --out <输出目录> \
    --fixed whitelist.txt --wild whitelist_wildcard.txt --tag white-guard \
    --mode exact \
    --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt
```

⚠️ 白名单**必须** `--mode exact`（见"第一步：实测匹配语义"）。用 suffix 会把整片广告域放行。

碰撞判定三种关系：`exact`（等于黑名单精确条目）、`glob`（被黑名单通配规则匹配）、`sub`（是黑名单精确条目的子域——黑名单按后缀拦截，所以子域也会被误杀）。

实测效果：Jinx 白名单 **325 → 42 条**，裁掉的正是会造成副作用的那批（`github.com` / `dns.google` / `jsdelivr.net` / `dropbox.com` / `icloud.com` 等），保留的都是国内 App 域名（强制直连也无所谓）。

引用顺序：`白名单 DIRECT` → `黑名单 REJECT` → `常规分流`。

### 用户问"能不能不上白名单"时怎么答

**技术可行**——黑名单独立工作，删掉白名单那行不影响拦截。但要讲清代价，别只说"行/不行"：

1. **量化误杀面**：guard 里每条都去黑名单回溯命中规则，按功能归类。Jinx 42 条的分布：推送 13（jpush/getui/gepush）、登录认证 2（`dypnsapi.aliyuncs.com` 一键登录、`apd-pcdnwxlogin` 微信登录）、网络/DNS 2（`httpdns.meituan.com`、`aedns.weixin.qq.com`）、字节 SDK 6、其他 App 功能 19。**推送和登录是用户可直接感知的故障**，这是劝留的主要理由。
2. **黑名单多为父域后缀规则**（`SUFFIX:jpush.cn`），误杀范围是整个域名家族，不只是 guard 里列出的那几个子域。
3. **无法用"从黑名单里扣掉白名单条目"替代**：黑名单后缀 vs 白名单精确，扣减会过度放行整族。要精确放行只能单独挂白名单规则集。
4. **用客户端日志验证误杀率**：统计日志里 `allowed` 域名被黑名单命中的条数。实测 Jinx 某手机 46 条记录中 `allowed` 16 条，误杀 **0 条**——说明 guard 命中的是长尾场景，短期不上不会立刻出问题。
5. **白名单不削弱去广告效果**（只放行 42 个功能域名），成本是 1 行配置。默认建议：保留。
6. **方向澄清（最常被误解）**：用户常问"是不是黑白名单一起用就不会误拦截"。要分开讲：白名单**只做减法**，不会增加任何拦截——若痛点是"广告还去不掉"，加白名单毫无帮助；它防的是反方向的病（推送/登录被误杀）。且"一起用"只消除**上游作者已知的**冲突，"零误杀"保证不了（黑名单自身的超广规则会打到白名单未覆盖的域名，见"踩坑记录"）。
7. 顺带提醒：SOP 里若写了 `RULE-SET,...,DIRECT,pre-matching`，那是无效写法——`pre-matching` 只支持 REJECT 系策略。

## 对外交付：必须写 README

把规则文件托管成公开仓库时，**必须**附 `README.md`，否则使用者（包括未来的自己）无从下手。必备八块：

1. **来源与致谢 + 许可状态**：写清上游仓库链接、对应版本、上游是否声明 License（无声明就明确写"无，本仓库不主张许可"）。**绝不把转换产物的版权据为己有**，并给出下架渠道（"作者提 issue 即删"）。
2. **选文件决策表**：按"你已有的规则集 / 客户端 / 保真 vs 性能"三档给结论，别让用户自己猜文件名。
3. **可直接复制的配置片段**：每个客户端一段，含**规则顺序警告**和参数说明。
4. **双地址**：每个文件同时给 jsDelivr 与 GitHub raw 两种 URL（见下"托管到公网"节）。
5. **已知坑**：超广通配误杀、高性能格式丢中缀通配、CDN 缓存、顺序、参数限制。
6. **重新生成方式（含脚本本体）**：只给命令**不算可复现**——脚本必须**随仓库一起上传**（放 `skill/` 或 `tools/` 目录），README 里写全"clone 下来就能跑"的流程（取源文件 → 跑脚本 → 覆盖上传），并标注源文件在上游的准确路径。实测教训：README 里只写 `python convert_ruleset.py ...` 而仓库无此脚本，使用者第一行就报 `can't open file 'convert_ruleset.py'`。
7. **告知可复现性是"已实测"的**：重跑一遍并与仓库现存文件做 `diff`，把结果写进 README（"逐字节一致"）。这既是给使用者的信心，也是自己下次改动时的回归基线。
8. **客户端前置开关 / 环境陷阱（最容易被漏掉的一块）**：规则本身完全正确，也可能因为客户端的一个开关而**静默失效**——没有报错、规则命中日志也正常，但流量根本没走规则。**这类内容必须单独成节，不能塞进"已知坑"一笔带过**，它是"规则配了却没效果"的头号原因。至少覆盖：
   - **OpenClash / mihomo**：开着「绕过中国大陆 IP」（`china_ip_route=1`）时，OpenClash 生成配置阶段会把 `rule-set:oc-cn-domain` 注入 `dns.fake-ip-filter`（源码 `/usr/share/openclash/yml_change.sh`）→ 命中该集合的域名 DNS 返回**真实 IP**（不是 `198.18.x.x`）→ 又在防火墙层被 `ip daddr @china_ip_route … return` 放行 → **流量不进内核，规则引擎没有机会执行**。
     - 判据：某域名在规则集里查得到，但客户端日志 `grep` 返回 **0 条**（没进内核 = 没日志）；或抓 DNS 看同一设备上并存"真实 IP"与"fake-ip"两种应答。
     - 解法：`uci set openclash.config.china_ip_route='0'` + commit + restart。副作用仅"域名访问多一跳内核"，纯 IP 直连不受影响。
   - **Surge**：`pre-matching` 只能跟 REJECT 系策略（DIRECT 加它无效）；`extended-matching` 是"App 直连 IP 时按 TLS SNI / HTTP Host 兜底匹配"的关键，缺了它域名规则会大批失效。
   - 通用验收三步：① DNS 应答从真实 IP 变 fake-ip；② 请求被拒（连接/TLS 失败）；③ 日志出现 `match RuleSet(<名字>) … using REJECT`。

参考实现：`jinx-ads-rules` 仓库 README 的 §五「OpenClash 实战陷阱」即为该块的标准写法。


## 托管到公网（Surge 必需）

Surge 只能引用 **URL 或本地文件**；mihomo 可用本地文件。用 `scripts/upload_to_github.py` 一步建库并上传：

```bash
python upload_to_github.py --token <PAT> --repo jinx-ads-rules --files a.list b.list
```

- **Token 最小权限**：classic 只勾 `public_repo` 即可（能建公开仓库+传文件，动不了私有代码）；fine-grained 需 Contents(read/write) + Administration(read/write)。
- **仓库必须 public**：私有仓库的 raw 地址要认证，Surge 拉不到。
- **引用优先 jsDelivr 镜像**：`https://cdn.jsdelivr.net/gh/<user>/<repo>@main/<file>`。`raw.githubusercontent.com` 国内常被墙；jsDelivr 有 CDN 缓存，但更新后有几分钟延迟。
- **README 与配置片段里两种地址都要给**（不要只给 jsDelivr）：jsDelivr 国内可直连但受 CDN 缓存/单点故障影响，`raw` 无缓存延迟但需能直连 GitHub。做法是——配置片段里把 raw 那行注释掉放在 jsDelivr 下一行，文末"文件清单"再给一张 `jsDelivr | raw` 双列速查表（或声明两个前缀 + 文件名拼接）。README 里不要出现"只推荐一个、另一个自求多福"的写法。
- **删除文件后必须 purge jsDelivr 缓存**：CDN 会继续提供已删文件（`raw` 已 404，但 `cdn.jsdelivr.net` 仍返回 200，两者不一致）。逐文件请求 `https://purge.jsdelivr.net/gh/<user>/<repo>@main/<file>`，返回 `"status": "finished"` 即生效，之后即 404。
- **删旧文件前先确认引用方已迁移**：规则集 URL 404 会导致客户端拉取失败。若无法确认，宁可保留旧文件并在 README 标注废弃（本次用户明确要求删除才删）。删除时保持**仓库名、文件名、CDN 域名不变**，只移除旧文件。
- 完成后提醒用户撤销 token（`github.com/settings/tokens`）。

## 踩坑记录

- **Surge 文件后缀别乱起**：`.conf` 是 Surge **主配置文件（profile）专用**。远程 RULE-SET 社区惯例是 `.list`，DOMAIN-SET 常见 `.txt`。后缀本身不影响 Surge 解析（按内容识别），但用 `.conf` 会让人误以为是 profile，属命名错误。
- **超广通配会误杀，且白名单救不了**：`ad.*`、`ad-*` 这类一条覆盖几百条的规则（实测 `ad.*` 单条吃掉 855 条精确条目）。转 `DOMAIN-REGEX` 后任何 `ad.xxx.com` 都被拒。**检测方法**：把规则集里所有 REGEX / WILDCARD 逐条去匹配一批真实正常域名（知名站点 + 客户端日志里的 `allowed` 域名），命中即潜在误杀。实测 Jinx 149 条 REGEX 中 84 条属"仅一段固定标签"的宽泛规则，用 49 个正常域名打入即命中 3 条（`^pangolin.*$` 命中 `pangolinstore.com`、`^adx\..*\.com$` 命中 `adx.example.com`、`^jad\-api\..*\.com$` 命中 `jad-api.qq.com`）。**这类误杀对象不在上游白名单里 → 白名单预知不了**，只能靠运行观察。
- **脏数据**：源文件里会混进 URL 式条目（如 `https://us.l.qq.com/exapp`、`https://ynuf.aliapp.org/savewb.json?`）。**不要整条丢弃**——用正则取出 host 后按普通域名规则处理（`host_of()`），否则白丢几条真实广告域。
- **旧产物别急着从仓库删**：用户客户端可能仍引用着旧 URL，删掉会导致规则集拉取失败、代理直接挂掉。改成"新文件名 + README 标注旧文件已废弃"更安全。
- **mihomo 日志/API 没有 URL 字段**：只有 host / sniffHost，没有 path。别指望从日志还原完整下载地址（详见下方"定位规则源"）。
- **`reduce-memory` 不是 mihomo 配置项**（SEO 站编的）；`GOMEMLIMIT` 只能注入环境变量，不是 YAML 字段。

## 定位规则源（拿不到 HTTPS 路径时）

抓包只能拿到域名（SNI / DNS），路径在 TLS 内。**成本更低的办法**：拿 App 侧强特征（更新时的文件名、版本号、目录结构、报错文案）去搜 GitHub / 代码搜索，再用其中的数据（版本号、条目数）与 App UI 显示交叉校验——从"像"升级为"就是"。

实例：用户给出 Jinx 更新时的 8 个文件名 → 直接命中 `VME98/jinx-rules` → `version.json` 的 `version` 和 `domainBlacklistCount` 与 App 显示完全一致 → 坐实。
