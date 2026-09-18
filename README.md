# Jinx Ads Rules —— 给 mihomo / Surge 用的转换版规则集

把 iOS 去广告 App **Jinx**（极简广告拦截与隐私保护）的黑名单，翻译成 **mihomo（Clash.Meta / OpenClash）** 与 **Surge** 可以直接引用的规则集格式。

## ⚠️ 先读这段

- **本仓库不是 Jinx 官方项目**，与 Jinx App 开发者无关。
- **本仓库不包含任何原创规则内容。** 全部域名数据来自上游开源仓库 **[`VME98/jinx-rules`](https://github.com/VME98/jinx-rules)**（Jinx 的远程规则仓库，本版对应上游 `version.json` 里的 **3.1.9**）。数据权利归上游作者所有。
- 本仓库唯一做的事情是：**语法翻译**（Jinx 的 glob 通配 → mihomo / Surge 的等价写法）**＋ 格式整理**。
- 上游仓库**没有声明任何开源许可**（`license: null`）。因此本仓库同样不主张任何许可，也不提供任何担保。如果你是上游作者、不希望这些转换产物被分发，提一个 issue，我会立即下架。
- 广告规则本质是"猜测 + 经验"，**误杀是常态**。上线前请先小范围验证，出问题先看第五节和第六节。

---

## 目录

- [一、先选文件](#一先选文件)
- [二、mihomo / OpenClash 怎么配](#二mihomo--openclash-怎么配)
- [三、Surge 怎么配](#三surge-怎么配)
- [四、为什么顺序是生死线](#四为什么顺序是生死线)
- [五、白名单：为什么推荐只用 42 条那份](#五白名单为什么推荐只用-42-条那份)
- [六、已知坑](#六已知坑)
- [七、数据来源与转换规则](#七数据来源与转换规则)
- [八、上游更新后怎么重新生成](#八上游更新后怎么重新生成)
- [九、许可与免责](#九许可与免责)

---

## 一、先选文件

### 第 1 步：你有没有在用别的广告规则集？

| 你的情况 | 用哪个 | 为什么 |
|---|---|---|
| **已经装了 `AWAvenue-Ads` / `anti-AD` / `GOODBYEADS` 等**（大多数人） | **`*-delta-*`（3011 条）** | 已经覆盖的 874 条不再重复加载 |
| **什么都没装，就想要一份完整的** | **`*-ads-*` 完整版（3885 条）** | |

两份内容同源，只是 delta 版扣掉了已经在用 AWAvenue 的部分。

### 第 2 步：按客户端选后缀

**mihomo / Clash.Meta**

| 文件 | 条数 | behavior | 保真度 |
|---|---:|---|---|
| `mihomo-ads-delta-classical.list` ⭐ | 3011 | `classical` | **100%** |
| `mihomo-ads-classical.list` | 3885 | `classical` | **100%** |
| `mihomo-ads-domain.list` | 3736 | `domain` | 丢 149 条中缀通配 |

**Surge**

| 文件 | 条数 | 引用方式 | 保真度 |
|---|---:|---|---|
| `surge-ads-delta-ruleset.list` ⭐ | 3011 | `RULE-SET` | **100%** |
| `surge-ads-ruleset.list` | 3885 | `RULE-SET` | **100%** |
| `surge-ads-domainset.txt` | 3736 | `DOMAIN-SET` | 丢 149 条中缀通配 |

> **★ 默认就用 `.list`（RULE-SET / classical）。**
> `domain` 和 `DOMAIN-SET` 这两种"高性能格式"装不下中缀星号（如 `p*-ad.adkwai.com`），会丢 149 条。3000 条的量级下，性能差异可以忽略，不值得为它丢规则。
> 只有当你真的在意内存、且能接受这 149 条失效时，才换用 `domain` / `DOMAIN-SET` 版本。

### 第 3 步：白名单（可选但建议）

| 文件 | 条数 | 用不用 |
|---|---:|---|
| `*-white-guard-*` ⭐ | **42** | **推荐**，只放行会被误杀的 |
| `*-white-*`（完整白名单） | 325 | 见 [第五节](#五白名单为什么推荐只用-42-条那份)，直接全量前插有副作用 |

---

## 二、mihomo / OpenClash 怎么配

### 远程引用（推荐，自动更新）

```yaml
rule-providers:
  jinx-white-guard:
    type: http
    behavior: classical
    format: text
    url: "https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-white-guard-classical.list"
    path: ./rule_provider/jinx-white-guard.list
    interval: 86400

  jinx-ads-delta:
    type: http
    behavior: classical
    format: text
    url: "https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/mihomo-ads-delta-classical.list"
    path: ./rule_provider/jinx-ads-delta.list
    interval: 86400

rules:
  # ① 先放行会被误杀的（必须排在 REJECT 之前）
  - RULE-SET,jinx-white-guard,DIRECT

  # ② 再拒绝广告
  - RULE-SET,jinx-ads-delta,REJECT
  - RULE-SET,AWAvenue-Ads,REJECT

  # ③ 之后才是常规分流
  - GEOSITE,cn,直连
  - GEOIP,CN,直连
  # ...
  - MATCH,🐟 漏网之鱼
```

### 本地文件引用

把 `.list` 传到路由器（如 `/etc/openclash/rule_provider/`），改用 `type: file`：

```yaml
rule-providers:
  jinx-ads-delta:
    type: file
    behavior: classical
    format: text
    path: ./rule_provider/jinx-ads-delta-classical.list
    interval: 86400
```

> **OpenClash 用户注意**：OpenClash 会覆写 `rule-providers` 与 `rules` 段。要持久生效，请写进「插件设置 → 覆写设置」或使用自定义配置文件，并确认最终运行文件里能看到这两条规则。改完务必先 `clash_meta -t` 校验再重启，否则内核起不来会直接断网。

---

## 三、Surge 怎么配

把下面两行加到 profile 的 `[Rule]` 段**最前面**：

```
[Rule]
# ① 先放行会被误杀的 42 条（普通匹配；pre-matching 只能配 REJECT 系策略，写在这里无效）
RULE-SET,https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-white-guard-ruleset.list,DIRECT

# ② 再拒绝广告
RULE-SET,https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/jinx-ads-rules@main/surge-ads-delta-ruleset.list,REJECT,pre-matching,extended-matching

# ③ 之后才是你原有的分流规则
```

### 两个参数为什么建议加上

| 参数 | 作用 | 依据 |
|---|---|---|
| `pre-matching` | 让 REJECT 提前到 **DNS 查询阶段 + TCP 握手阶段**生效，App 还没连上就被掐断 | 这是 Surge 官方文档里明确说明的行为，也是**最接近 Jinx 原生体验**的形态（Jinx 靠系统级 DNS 拦截） |
| `extended-matching` | 除域名外，额外用 **TLS SNI / HTTP Host** 匹配 | 专治"App 直连 IP 导致域名规则不生效"的漏网情况 |

两个可以叠加，写成 `REJECT,pre-matching,extended-matching`。

### 两个关于参数的硬约束（容易踩）

1. **`pre-matching` 只支持 REJECT 系策略**——写在 `DIRECT` 行上没有意义。所以白名单那行不要加。
2. **`pre-matching` 不能写进规则集文件内部**——只能写在 profile 的 `RULE-SET` 行上。规则集文件里出现它会被当无效行跳过。（本仓库的 `.list` 里没有写，放心。）

---

## 四、为什么顺序是生死线

mihomo 和 Surge 都是**自上而下、命中即停**。这意味着：

```
❌ 错误顺序
RULE-SET,域名大全,Direct      ← 国内域名在这里就被放走了
RULE-SET,jinx-ads,REJECT      ← 永远轮不到，等于白加
```

```
✅ 正确顺序
RULE-SET,jinx-white-guard,DIRECT   ← 白名单先放行
RULE-SET,jinx-ads,REJECT           ← 黑名单再拒绝
RULE-SET,国内直连,DIRECT            ← 常规分流最后
```

**你原来"用 AWAvenue-Ads 去不掉"很可能就踩了这条**：如果 REJECT 规则集排在 `GEOSITE,cn,DIRECT` 或 `GEOIP,CN,DIRECT` 后面，国内 App 的广告域名会先被"国内直连"截胡，广告规则一次都不会被求值。

加分项：mihomo 里 `REJECT` 也可以替换成 `REJECT-DROP`（直接丢包，不返回 RST），对某些会重试的 App 更干净，代价是偶尔会多等一个超时。

---

## 五、白名单：为什么推荐只用 42 条那份

上游白名单有 **325 条**，但把它整份插到 REJECT 前面当 `DIRECT` 会有**副作用**——它里面包含：

```
github.com          raw.githubusercontent.com    dns.google
cloudflare-dns.com  jsdelivr.net                dropbox.com
onedrive.live.com   icloud.com                  mail.qq.com
```

这些都是"作者为了防止**其他**规则集误杀"而放进去的。**如果整份放在最前面走 DIRECT，会把 github / dns.google / dropbox / onedrive 全部强制直连**——对国内网络环境来说，这几乎是帮倒忙（这些域名往往正需要走代理）。

**真正的白名单只需要"会被当前黑名单误杀"的那部分。** 我按下面的规则算了一遍：

| 白名单条目 | 条数 |
|---|---:|
| 完全不与黑名单冲突（放进去只会造成上表的副作用） | 282 |
| **真的会被黑名单误杀（需要保留）** | **42** |

所以 `*-white-guard-*` 就是这 42 条：

```
zlink.ugsdk.cn   praisewindow.ugsdk.cn   cactus.jd.com
effect.snssdk.com   tnc3-aliec2.snssdk.com   mssdk.bytedance.com
user.jpush.cn   s.jpush.cn   httpdns.meituan.com   oneid.getui.net
aedns.weixin.qq.com   p.l.qq.com   appcfg.v.qq.com   ...（共 42 条）
```

这 42 条基本都是国内 App 的域名，**即使强制直连也是本来就走直连的**，所以没有副作用。

> 这 42 条是按**完整黑名单**算的。如果你用的是 delta 版，其中 20 条严格来说仍在 delta 黑名单里、另外 22 条则是因为 AWAvenue 也可能拦它们才保留——两种部署都用同一份，不用改。

**什么时候才需要完整 325 条那份？** 当你同时还挂了别的、覆盖面很杂的规则集时，可以拿它做全局 DIRECT 白名单——但要清楚它会把你上面的那些域名一并强制直连。

---

## 六、已知坑

1. **超广通配是误杀头号嫌疑**
   上游黑名单里有 `ad.*`、`ad-*`、`ads.*`、`pangolin*` 这类规则，**一条就能覆盖几百个域名**（`ad.*` 单条约等于 855 条精确规则）。某个 App 突然连不上，先怀疑这几条——临时把它注释掉验证。

2. **中缀星号在两种格式下会丢**
   `p*-ad.adkwai.com` 这类共 149 条，**只有 mihomo `classical` / Surge `RULE-SET` 装得下**；`domain` / `DOMAIN-SET` 会静默丢弃。

3. **`*.x.com` 不含裸域 `x.com`**
   标准 glob 语义。本仓库统一按"跨级 + 含裸域"放宽（转成 `DOMAIN-SUFFIX`），对黑名单来说是宁可多拦、更安全；但副作用是解析行为与 Jinx 原文略有差异。

4. **CDN 有缓存**
   jsDelivr 更新后有几分钟到几小时延迟。想立刻生效，把 `@main` 换成具体的 commit SHA。

5. **内容端到端不可校验**
   规则集是明文 HTTP 拉下来的，无法验证签名。所以请用**你自己的仓库地址**（本仓库）而不是随便引用他人链接——你至少能确认自己仓库里的内容。

6. **本仓库是快照，不会自动跟随上游**
   上游更新后需要重新跑一次转换，见下一节。

7. **别把白名单放在 REJECT 之后**
   放在后面 = 无效。

---

## 七、数据来源与转换规则

### 上游

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/VME98/jinx-rules |
| 说明 | Jinx App 的远程规则仓库模板 |
| 版本 | `version.json` → `3.1.9`（`lastUpdate` 2026-09-15） |
| 许可 | **无**（仓库未声明 License） |

上游 `version.json` 原文（用于核对，App 显示的条数应与之一致）：

```json
{ "version": "3.1.9",
  "lastUpdate": "2026-09-15T14:35:01Z",
  "domainBlacklistCount": 3888,
  "domainWhitelistCount": 325,
  "urlBlacklistCount": 890,
  "urlWhitelistCount": 21,
  "mitmSkipDomainsCount": 33 }
```

### 语法映射

三家对 `*` 的定义**互不相同**，所以不能原样引用。mihomo 官方语法规定 `*` 只匹配一级、不跨点，而 Jinx 的 `*` 是标准 glob（跨点、可内嵌）：

| Jinx 写法 | mihomo（classical） | Surge |
|---|---|---|
| `x.com` | `DOMAIN,x.com` | `DOMAIN,x.com` |
| `*.x.com` | `DOMAIN-SUFFIX,x.com` | `DOMAIN-SUFFIX,x.com` |
| `p*-ad.x.com` | `DOMAIN-REGEX,^p.*-ad\.x\.com$` | `DOMAIN-WILDCARD,p*-ad.x.com` |
| `https://…`（脏数据） | 丢弃 | 丢弃 |

统一按"跨级 + 含裸域"放宽（理由见第六节第 3 条）。

### 产物规则类型分布

| 文件 | 规则数 | 构成 |
|---|---:|---|
| `mihomo-ads-classical.list` | 3885 | DOMAIN 3670 / DOMAIN-SUFFIX 66 / DOMAIN-REGEX 149 |
| `surge-ads-ruleset.list` | 3885 | DOMAIN 3670 / DOMAIN-SUFFIX 66 / DOMAIN-WILDCARD 149 |
| `*-ads-delta-*` | 3011 | DOMAIN 2807 / SUFFIX 62 / 通配 142 |
| `*-ads-domain*` / `*-domainset*` | 3736 | 同上，但丢弃 149 条中缀通配 |
| `*-white-*`（完整） | 325 | DOMAIN 283 / DOMAIN-SUFFIX 38 / DOMAIN-WILDCARD 4 |
| `*-white-guard-*` | 42 | DOMAIN 41 / DOMAIN-SUFFIX 1 |

### 上游文件里**没有**被转换的部分

`url_blacklist.txt`、`url_whitelist.txt`、`mitm_skip_domains.txt`、`url_response_policies.json` 等文件**不在本仓库内**，因为它们依赖 MITM + URL 层拦截能力，mihomo / Surge 的域名规则无法表达。本仓库只转换纯域名黑/白名单。

---

## 八、上游更新后怎么重新生成

转换逻辑固化成了一个可复用脚本（不依赖本仓库）：

```bash
# 1) 拉上游最新规则
git clone https://github.com/VME98/jinx-rules

# 2) 黑名单 -> mihomo + Surge（含与 AWAvenue 的差集）
python convert_ruleset.py --src ./jinx-rules --out ./converted \
    --fixed blacklist.txt --wild blacklist_wildcard.txt --tag ads \
    --delta-ref https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule-Clash-Classical.yaml

# 3) 白名单瘦身：只保留会被黑名单误杀的
python convert_ruleset.py --src ./jinx-rules --out ./converted \
    --fixed whitelist.txt --wild whitelist_wildcard.txt --tag white-guard \
    --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt
```

<sub>脚本见本仓库 issue 或作者本地 skill `adblock-ruleset-port`。核心是三步：分类 → 语法翻译 → 差集/碰撞过滤。</sub>

---

## 九、许可与免责

- **规则数据**：版权与权利归上游 [`VME98/jinx-rules`](https://github.com/VME98/jinx-rules) 作者。上游未声明 License，本仓库亦**不主张任何许可**，仅作格式转换后的转载与整理。
- **转换产物**：可自由取用，但请**保留本仓库与上游仓库的链接**，不要抹去来源后二次分发。
- **免责**：广告拦截必然存在误杀与漏拦，且域名列表随时可能变更。请自行验证后再长期使用，作者不对因使用本规则集导致的任何网络异常负责。
- **下架请求**：若你是上游作者或权利方且不希望这些产物被分发，请提 issue，我会立即删除仓库。
