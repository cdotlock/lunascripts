# Lunascripts (LS) 语法规范

> 本文件只定义语法：什么写法是合法的、编译器和引擎如何理解它。
> 至于怎么用这些语法把剧本写好——选择密度、检定档位、look 词表、CG 写作规范、
> signal 使用纪律等——由 lunaverse-ide 里的各 skill（entity-planner、episode-writer 等）规定，
> 不在本文件。skill 只负责创作建议，不得增删或收紧本文件定义的合法语法。

> **契约版本：3.0.0（2026-08-06）。** 变更清单见附录 D。

---

## 1. 总则

### 1.1 文件

- 一个 `.ls` 文件 = 一集。UTF-8 纯文本，换行符 `\n`。
- `@episode` 头部的 `<branch_key>:<seq>` 是本集 ID；编译器不根据文件路径反推或比对 ID。

### 1.2 基本规则

| 元素 | 写法 | 说明 |
|---|---|---|
| 注释 | 行首 `//` | 编译器整行忽略。producer 工具另有一些注释标记约定（如 `// wardrobe-change:`），那是工具层契约，编译器不感知，见对应 skill |
| 空行 | — | 忽略，用于可读性分段 |
| 字符串 | `"..."` | 双引号包裹 |
| 块 | `{ }` | 可嵌套 |
| 指令 | `@` 前缀 | 如 `@bg school_hallway` |
| 并发指令 | `&` 前缀 | 与前一条 `@` 指令同时执行，见 §4 |
| 对话行 | `角色名: 文本` | 角色名全大写，无前缀 |

### 1.3 舞台规则（引擎语义）

- **MC**（玩家扮演的角色）固定在屏幕**左侧**，**其余角色**全部固定在**右侧**，位置不可指定。
- **同屏一人**：任意时刻最多显示一个角色。
- `@<char> <look>` 立即显示该角色或切换其立绘；角色对白使用该角色最近一次声明的 look。每个角色在本集首次对白前必须声明 look。
- `YOU:` 由前端自动显示 MC，使用 MC 最近一次声明的 look；MC 在本集首次 `YOU:` 前必须声明 look。
- 只有 `NARRATOR:` 会清空立绘。
- 引擎在运行时才知道谁是 MC（由前端业务层注入）。编译产物不携带 MC 身份信息。

### 1.4 指令分类一览

| 类别 | 指令 |
|---|---|
| 结构控制 | `@episode`、`@gate`、`@pause` |
| 视觉呈现 | `@<char> <look>`、`@<char> bubble`、`@bg`、`@cg` |
| 对话 | `CHARACTER:`、`NARRATOR:`、`YOU:`、`CHARACTER [look]:` |
| 手机/消息 | `@phone`、`@text` |
| 音频 | `@music`、`@sfx` |
| 交互原语 | `@trick`、`@minigame`、`@choice` / `@option` / `check` |
| 状态变更 | `@affection`、`@signal`、`@achievement`、`@butterfly` |
| 流程控制 | `@if` / `@else @if` / `@else` |
| 时序控制 | `&` 并发前缀 |

---

## 2. 指令宝典

每条指令一张卡，结构固定：**定义（一句话）→ 语法 → 参数表 → 示例 → 校验**。
没有参数的指令省略参数表。

### 2.1 结构控制

#### `@episode`

集定义，整个文件的根块，全部内容都在它里面。一个文件恰好一个。

```
@episode <branch_key>:<seq> "<title>" { ... }
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `branch_key:seq` | 是 | 集 ID | 如 `main:01` |
| `title` | 是 | 字符串 | 本集标题 |

**示例**

```
@episode main:01 "Three Place Settings" {
  // 全部内容
}
```

**校验**
- 缺少 `@episode` 头部或必填参数报错。

#### `@gate`

路由声明块，声明本集所有出口：跳去下一集，或终结剧情。每集**恰好一个**。

```
@gate {
  @if (<condition>): @next <branch_key>:<seq>
  @else @if (<condition>): @end <type>
  @else: @next <branch_key>:<seq>
}
```

**块内出口规则**

| 规则 | 说明 |
|---|---|
| `@next <branch_key>:<seq>` | 路由到指定集 |
| `@end <type>` | 终结剧情，`type` 三选一见下表 |
| `@if (<condition>): ...` | 条件出口，条件写法见 §3 |
| `@else @if (<condition>): ...` | 链式条件，可连续多个 |
| `@else: ...` | 兜底分支 |

| ending type | 含义 | 典型用法 |
|---|---|---|
| `complete` | 全剧终 | 主线大结局、角色 Happy End |
| `to_be_continued` | 待续 | 本季/本章完，下一章未写 |
| `bad_ending` | 坏结局 | 坏路线终点、玩家出局 |

**示例**——最简形态与条件混合：

```
@gate { @next main:02 }

@gate { @end bad_ending }

@gate {
  @if (REJECTIONS >= 3): @end bad_ending
  @else @if (HEROIC_END): @end complete
  @else: @next main:02
}
```

**校验**
- 缺 `@gate` 报 `MISSING_TERMINAL`。
- 条件链必须完整覆盖：要么单个无条件出口，要么含 `@else` 兜底的完整 `@if` 链。
- **没有独立的 `@ending` 指令**，终结只能通过 gate 内的 `@end` 表达。

#### `@pause`

等待玩家点击一次后继续。

```
@pause
```

**校验**
- 无参数。

### 2.2 视觉呈现

#### `@<char> <look>` —— 显示角色 / 切换立绘

显示角色立绘或切换其 look。首次出现自动入场，再次出现切 look。

```
@<char> <look> [transition]
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `char` | 是 | 角色 ID（小写） | 立绘挂在谁身上 |
| `look` | 是 | 立绘素材键 | 编译器当**不透明字符串**原样透传进产物（产物字段名 `look`），存量旧键全兼容。新内容的命名规范 `<char>__<outfit>__<神态>[-<动作>]` 及词表由 producer 工具强制（episode-writer skill + IDE lint），不归编译器管 |
| `transition` | 否 | `dissolve` / `fade` / `cut` / `slow` | 角色过渡效果 |

**示例**

```
@seren seren__urban_arrival__drained
@dean dean__winter_fireside__deadpan-arms_folded dissolve
```

**校验**
- 编译器不校验 look 内容；owner 一致性、词表白名单由 producer 层拦截。
- 引擎记忆每个角色最后一次的 look，再次说话时默认沿用；要换 look 用本指令或对白糖 `CHAR [look]:`。

#### `@<char> bubble` —— 气泡动画

在当前角色头上播放一次性情绪气泡，播完自动消失。

```
@<char> bubble <type>
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `char` | 是 | 角色 ID（小写） | 气泡跟随该角色 |
| `type` | 是 | 9 个锁定值见下表 | 气泡样式 |

| type | 效果 | type | 效果 | type | 效果 |
|---|---|---|---|---|---|
| `anger` | 💢 怒气 | `question` | ❓ 疑惑 | `music` | 🎵 开心/哼歌 |
| `sweat` | 💧 冷汗 | `exclaim` | ❗ 惊讶 | `doom` | 💀 绝望 |
| `heart` | ❤️ 心动 | `idea` | 💡 灵机一动 | `ellipsis` | … 沉默/无语 |

**示例**

```
@josie bubble heart
```

**校验**
- `bubble` 是保留字，look 不可与之同名。
- 角色被切走时气泡随之消失。

#### `@bg` —— 切换背景

切换全屏背景。

```
@bg <name> [transition]
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `name` | 是 | 背景素材语义名 | 经素材映射表解析（§5） |
| `transition` | 否 | 见下表 | 不写 = 交叉溶解 |

| transition | 效果 |
|---|---|
| `dissolve` | 交叉溶解 |
| `fade` | 淡入 |
| `cut` | 直切 |
| `slow` | 慢速过渡 |

**示例**

```
@bg voss_house_kitchen_evening fade
```

**校验**
- transition 超出合法值报错。
- 新内容使用 `@bg <name> [transition]`；编译器仍接受存量写法 `@bg set <name> [transition]`。

#### `@cg` —— 全屏 CG

全屏 CG 展示。最终交付可以是静态图、视频或动态漫画，由生产阶段选择，脚本只声明语义名和叙事描述。

```
@cg <name> "<content>"
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `name` | 是 | 素材句柄 | 对应素材映射 `assets.cg.<name>` |
| `content` | 是 | 英文现在时场景描述 | 编译器不解析其内容，原样透传 |

**示例**（取自实际生产剧本）

```
@cg door_slam_face "Night in @bg_voss_house_hallway_night, a single work lamp spilling from the doorway. @seren__urban_arrival__stunned_blank stands mid-sentence, one hand half-raised, lips parted. Inside the room @knox__shadow_default__cold_dismissal is already turning away, his arm driving the door shut."
```

**校验**
- 单行叶子指令，无 `{ }` 块。
- 编译器只查形态；content 的写作规范（分镜式写法、`@角色__outfit__神态[-动作]` 完整 sprite 标签与 `@bg_<name>` 内嵌标签、道具独立成句、视频形态的精修流程等）全部由 episode-writer skill 规定。

### 2.3 对话

对话行不用 `@` 前缀，通过行首全大写角色名识别。每条对话行独立推进，等玩家点击。

#### `CHARACTER:` —— 角色对白

角色对白。说话角色自动显示，与上一个说话者不同时自动切换。

```
@<char> <look>
CHARACTER: 文本
```

**台词行本身不携带立绘信息**——引擎显示的是该角色**最近一次声明的 look**。
所以标准写法是台词行之前先用 `@<char> <look>` 声明立绘（换表情同理），
或者用对白糖 `CHARACTER [look]:` 一行完成。角色本集首次说话前必须有过 look 声明。

**示例**

```
@dean dean__winter_fireside__tight_lipped
DEAN: You're late.

DEAN: Rules are rules.
```

**校验**
- 角色名在编译产物中统一转小写。

#### `CHARACTER [look]:` —— 换装对白糖

切 look + 对白，一行完成。等价于 `@character look` + `CHARACTER: 文本` 两行。

```
CHARACTER [look]: 文本
```

**示例**

```
DEAN [dean__winter_fireside__cold_dismissal]: After seven, you stay in your room.
```

**校验**
- `look` 同 `@<char> <look>` 的两层规则：编译器透传，命名规范由 producer 层强制。

#### `NARRATOR:` —— 旁白

旁白，MC 视角但有叙事距离。

```
NARRATOR: 文本
```

**示例**

```
NARRATOR: Senior year. Day one.
```

**校验**
- 出现时**清空所有立绘**。
- 旁白中指代 MC 的人称规范（大写 YOU/YOUR）属写作规范，见 episode-writer skill。

#### `YOU:` —— MC 内心独白

MC 第一人称内心独白，**显示 MC 立绘**。

```
@<mc_char> <look>
YOU: 文本
```

与角色对白同理：`YOU:` 行本身不携带立绘信息，显示的是 MC 最近一次声明的 look，
所以 `YOU:` 之前要用 `@<mc_char> <look>` 声明 MC 立绘（换表情同理）。

**示例**

```
@seren seren__urban_arrival__lost_in_thought
YOU: Another year. Same mess.
```

**校验**
- 与 `NARRATOR` 的区别：`NARRATOR` 清屏、是有距离感的观察描述；`YOU` 带 MC 立绘、是此刻的内心思考。

### 2.4 手机/消息

#### `@phone` + `@text`

弹出手机短信界面，块结束自动收起。

```
@phone {
  @text from <char>: 内容
  @text to <char>: 内容
}
```

**参数**（`@text`）

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `from` / `to` | 是（二选一） | — | `from` = 发件人；`to` = 收件人 |
| `char` | 是 | 角色 ID | 编译产物统一转小写；UI 根据角色 ID 解析显示名 |

**示例**

```
@phone {
  @text from EASTON: Can we talk? I miss you.
  @text to MAURICIO: How do you know where I live?
}
```

**校验**
- **必须多行**：`@phone {` 换行、逐条 `@text`、换行 `}` 收尾。单行内联 `@phone { @text ... }` 解析器不接受。
- 块内**只允许 `@text`**——旁白、音效、状态变更必须放块外。
- 块内一律**不发声**，不需要配音绑定。

### 2.5 音频

#### `@music`

播放/停止 BGM。

```
@music <name>
@music stop
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `name` \| `stop` | 是 | 曲名语义名，或关键字 `stop` | `name` 设置 BGM；`stop` 停止 BGM |

**示例**

```
@music grief_suspense
@music stop
```

#### `@sfx`

一次性音效。

```
@sfx <name>
```

**示例**

```
@sfx door_slam
```

### 2.6 交互原语

四个边界清晰的原语，把"打断剧情让玩家做点什么"拆开：

| 原语 | 强制性 | 奖励 | 叙事分支 | 实现 |
|---|---|---|---|---|
| `@trick` | 强制卡关 | 无 | 无 | 引擎原生（触摸/运动） |
| `@minigame` | 可选可跳 | 有（引擎侧） | 无 | WebView，下游 agent 生成 |
| `@choice` | 强制 | — | 有（真分支） | 引擎原生 |
| `@cg` | — | — | — | 下游按形态生产（见 §2.2） |

#### `@trick`

强制体感微交互，玩家完成动作后剧情才继续。

```
@trick <type> "<prompt>"
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `type` | 是 | `tap`（连点）/ `hold`（长按）/ `swipe`（滑动）/ `shake`（摇）/ `swing`（挥动）/ `tilt`（倾斜） | 6 个锁定值，脚本不能新增 |
| `prompt` | 是 | 非空字符串 | 给玩家看的一句祈使句 |

**示例**

```
@trick hold "Hold your breath until he walks past."
```

**校验**
- 单行叶子指令。type 超出 6 值报错；prompt 空串报错。
- 阈值（点几下/按多久）写死在引擎，脚本不传参。

#### `@minigame`

嵌在剧情里的可选小游戏，玩家可玩可跳，由下游 vibe-coding agent 按描述生成。

```
@minigame <name> "<description>"
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `name` | 是 | 素材句柄 | 对应 `assets.minigames.<name>` |
| `description` | 是 | 一整段连贯英文 prose | 衔接剧情 + 简单定义玩法；不分字段、不是 JSON |

**示例**

```
@minigame casino_showdown "Mauricio drags Malia into a backroom blackjack game — green felt, cigarette smoke, his friends watching — betting on who covers tonight's tab. The player taps to draw cards and taps Stand to hold, beating the dealer without going over 21; three quick rounds. Win and Malia keeps her dignity; lose and she owes him a favor."
```

**校验**
- 单行叶子指令。无属性、无评级分支、不参与 D20。
- 奖励全在引擎侧按回传分数缩放；玩家跳过 = 整条当 no-op。
- description 的质量要求（可生成的玩法复杂度上限等）由创作 skill 规定。

#### `@choice`

强制选择块，玩家必须选一个才能继续。块内只有 `@option`。

```
@choice {
  @option <ID> <brave|safe> "<text>" { ... }
  @option <ID> <brave|safe> "<text>" { ... }
}
```

**校验**
- 块内只允许 `@option`，且至少有两个；其他内容直接报错。

#### `@option`

一个选项及其后续内容。

```
@option <ID> <brave|safe> "<text>" { ... }
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `ID` | 是 | `A` / `B` / `C` … | 选项编号，供条件回顾 `@if (A.success)` |
| 模式 | 是 | `brave` / `safe` | `brave` 走 D20 检定，块内**必须**包含 `check { }`，结果分支用 `@if (check.success) { } @else { }`；`safe` 跳过检定，块内直接是叙事内容 |
| `text` | 是 | 字符串 | 玩家看到的选项文字 |

**校验**
- brave 缺 `check { }` 报错。
- `@if (check.success)` 只写成功分支、省略 `@else` 是**合法**的（省略时失败路径 = 什么都不发生），是否强制双分支由 skill 层决定。

#### `check`

D20 检定参数块，嵌套在 brave 选项内。注意无 `@` 前缀。

```
check {
  attr: <NAME>
  dc: <N>
}
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `attr` | 是 | 非空属性名 | 属性集合由业务定义 |
| `dc` | 是 | 正整数 | 难度值 |

**示例**——完整的 choice 结构：

```
@choice {
  @option A brave "Stand your ground." {
    check {
      attr: BOLD
      dc: 12
    }
    @if (check.success) {
      EASTON [easton__school_default__relieved]: Can I sit?
      @affection easton +2
    } @else {
      MALIA: I... I can't do this.
    }
  }
  @option B safe "Have Mark make a scene." {
    MARK: HEY EASTON! You want some of my mystery casserole?
    YOU: Thank god for Mark.
  }
}
```

**校验**
- 引擎公式：`D20(1-20) + 属性修正 >= DC → 成功`。
- 属性值只在检定公式内部参与计算，**`@if` 不能裸名读取属性**（见 §3.2）。按属性做分支用检定结果间接表达。
- **check 是 brave option 的参数，不是顺序步骤**；玩家选中该 option 时结算。

### 2.7 状态变更

脚本只做声明，引擎负责计算和持久化。引擎自己管理的数值（XP、SAN/HP 等）脚本**不能修改**，
只能在 `@if` 条件里读（名称由引擎定义，惯用小写，如 `san`）。

作者自定义的 signal（mark 和 int）统一使用英文 **`SCREAMING_SNAKE_CASE`**，
必须匹配 `^[A-Z][A-Z0-9_]*$`，`lsc validate` 机械拦截不合规命名。
大小写的分工：**全大写 = 作者 signal，小写 = 引擎数值**，两类状态不会互相冒充。

**检定属性不在这个命名空间里**：属性（`check` 的 `attr` 取值，集合由 planner skill 定义）
只存在于 `check` 块的 `attr` 槽位，参与 D20 检定公式的计算；`@if` 的裸名**不解析**检定属性。
要按属性高低做剧情分支，用 brave 检定的结果（`check.success` / `A.success`）间接表达。

#### `@affection`

调整角色好感度，引擎跨集存储。

```
@affection <char> <+N | -N>
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `char` | 是 | 角色 ID（小写） | 对谁的好感度 |
| 增量 | 是 | `+N` / `-N` | **正负都合法** |

**示例**

```
@affection easton +2
@affection dean -1
```

**校验**
- 读取用 `@if (affection.<char> >= 5)`（comparison 条件，见 §3）。

#### `@signal mark`

持久布尔标记，引擎永久存储。

```
@signal mark <EVENT>
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `EVENT` | 是 | 裸标识符或双引号字符串 | `SCREAMING_SNAKE_CASE`，validator 强制 |

**示例**

```
@signal mark HIGH_HEEL_EP05
```

**校验**
- 读取用 `@if (EVENT_NAME) { ... }`（flag 条件，见 §3）。
- mark 应当有 reader（有人在后续 `@if` 里查它）。何时打 mark、写-读配对纪律见 skill 层。

#### `@signal int`

持久整数变量，引擎跨集存储，适合计数型剧情锁。

```
@signal int <NAME> = <N>
@signal int <NAME> +<N>
@signal int <NAME> -<N>
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `NAME` | 是 | `SCREAMING_SNAKE_CASE` | validator 强制，与 mark 同规 |
| 操作 | 是 | `= N`（赋值，N 可为负）/ `+N`（增）/ `-N`（减） | `+N` / `-N` 中 N 非负，负增量用 `-N` 形态 |

**示例**

```
@signal int REJECTIONS +1
```

**校验**
- 首次引用视为 0。
- `=` 每次执行都无条件覆盖——放在集首会在玩家回放时清零，是作者的责任。
- 读取用裸名比较 `@if (REJECTIONS >= 3)`，与引擎数值同语法。

#### `@achievement`

成就解锁。执行到这条节点即解锁，条件触发由外层 `@if` 承担，同一 id 重复触发由引擎去重。

```
@achievement <ID> {
  name: "<显示名称>"
  rarity: <rarity>
  description: "<flavor 文本>"
}
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `ID` | 是 | `^[A-Z][A-Z0-9_]*$` | 成就 ID |
| `name` | 是 | 字符串 | 显示名称，英文短语 |
| `rarity` | 是 | `uncommon` / `rare` / `epic` / `legendary` | **没有 `common`** |
| `description` | 是 | 字符串 | 1-2 句英文 flavor 文本 |

**示例**

```
@if (HIGH_HEEL_EP05 && HIGH_HEEL_EP24) {
  @achievement HIGH_HEEL_DOUBLE_KILL {
    name: "Heel Twice Over"
    rarity: epic
    description: "Once is improvisation. Twice is a signature move."
  }
}
```

**校验**
- ID 必须匹配 `^[A-Z][A-Z0-9_]*$`。
- 三个字段全部必填；缺 `{ }` 的裸形式是 parse error。

#### `@butterfly`

蝴蝶效应记录——记录玩家行为及其性格含义，供后续内容生成流程理解玩家画像。

```
@butterfly "<description>"
```

**示例**

```
@butterfly "Accepted Easton's approach at the cafeteria"
```

**校验**
- **不参与运行时路由判定**——gate 求值不读 butterfly，所有路由依赖 signal、affection、choice 历史这些确定性状态。
- 描述文本的写作要求（语言、点名道姓写剧情影响、禁机制黑话）见 skill 层。

### 2.8 流程控制

#### `@if` / `@else @if` / `@else`

条件分支。`@else @if` 可链式接多个，`@else` 兜底可省略。

```
@if (<condition>) {
  ...
} @else @if (<condition>) {
  ...
} @else {
  ...
}
```

**参数**

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `condition` | 是 | 5 种条件类型，见 §3 | 必须用括号 `()` 包裹 |

**示例**

```
@if (affection.easton >= 5 && TIMES_YIELDED == 0) {
  EASTON: You remembered.
} @else @if (affection.easton >= 3) {
  EASTON: ...I wasn't sure you'd come.
} @else {
  EASTON: ...Hey.
}
```

**校验**
- gate 块内的 `@if` 是单行冒号形式（`@if (...): @next ...`），见 §2.1 `@gate`。

---

## 3. 条件表达式

`@if (...)` 括号里能写的东西。所有条件都被解析为结构化 AST，
后端直接遍历判定，不含表达式字符串。

### 3.1 五种条件类型

| 类型 | 源语法 | 含义 | 作用域 |
|---|---|---|---|
| choice | `<ID>.<result>` | 玩家之前选了某选项、结果如何。`result ∈ success / fail / any` | 任意位置 |
| flag | `SIGNAL_NAME` | 某布尔 mark 是否被打过 | 任意位置 |
| comparison | `<operand> <op> <operand>` | 数值比较 | 任意位置 |
| compound | `expr && expr` / `expr \|\| expr` | 组合条件，支持括号分组 | 任意位置 |
| check | `check.success` / `check.fail` | 当前选项刚掷的 D20 成没成 | **仅 brave 选项体内** |

`check` vs `choice` 的区别：`check.success` 问"**这个** option 刚刚的检定成了吗"（当前局部）；
`A.success` 问"玩家**之前**选了 A 且检定成功了吗"（历史回顾，任意位置可用）。

### 3.2 comparison 的操作数（operand）

| 形态 | 源语法 | 说明 |
|---|---|---|
| 字面量 | `5` / `-2` | 整数 |
| 好感度 | `affection.<char>` | 角色好感度 |
| 裸名数值 | `<NAME>` | 引擎数值（小写，如 `san`）或作者 `@signal int` 变量（全大写）。引擎按裸名查找。**检定属性不在此列**——属性只在 `check` 块内参与 D20 计算，`@if` 读不到 |
| 聚合 | `MAX(<op>, <op>, ...)` / `MIN(...)` | 取参数中的最大/最小值。参数 ≥ 2 个、无上限，可递归嵌套 |

**操作符**：`>=` `<=` `>` `<` `==` `!=`，左右两侧均可为任意 operand。

```
@if (affection.easton >= 5): @next main/route/001:01
@if (affection.easton > affection.diego) { ... }
@if (MAX(affection.easton, affection.diego, affection.mauricio) >= 8) { ... }
@if ((A.success || B.success) && affection.easton >= 3) { ... }
```

### 3.3 约束

- **不支持一元否定 `!`**。要否定布尔条件就交换 `@if` 与 `@else` 分支；`!=` 仍然合法。
- `||` 优先级低于 `&&`；用括号分组改变结合。
- `MAX` / `MIN` 是保留字，必须全大写；参数少于 2 个是 parse error。
- 比较类条件归 comparison，裸大写名归 flag——同一个名字不要一处当布尔一处当整数用。

---

## 4. 并发控制

用 `@` 和 `&` 前缀区分时序：

| 前缀 | 含义 |
|---|---|
| `@` | 顺序执行，开启一个新的步骤组 |
| `&` | 加入前一条 `@` 指令的步骤组，与之**同时执行** |
| （无前缀对话行） | 始终独立，等玩家点击 |

```
// 三条并发：切背景的同时起音乐、上立绘
@bg school_hallway fade
&music tense_strings
&mauricio mauricio__varsity_jacket__neutral_smirk

MAURICIO: Hey, Butterfly.
```

`&` 只能用于单行指令，并且必须加入前一条 `@` 开启的组。
`@choice`、`@phone`、`@if`、`@gate` 等块结构只能使用 `@`。

---

## 5. 素材映射

脚本与素材**分离**：脚本只写语义名，素材映射表是独立文件（由 Lunaverse IDE 素材管线维护），
编译时结合：`lsc compile script.ls --assets mapping.json -o output.json`。
好处：同一脚本可指向不同环境；换素材 URL 不改脚本；两条管线独立迭代。

映射表格式：

```json
{
  "base_url": "https://oss.mobai.com/novel_001",
  "assets": {
    "bg":         { "voss_house_kitchen_evening": "bg/voss_house_kitchen_evening.png" },
    "characters": { "seren": { "seren__urban_arrival__drained": "characters/seren__urban_arrival__drained.png" } },
    "music":      { "grief_suspense": "music/grief_suspense.mp3" },
    "sfx":        { "door_slam": "sfx/door_slam.mp3" },
    "cg":         { "door_slam_face": "cg/door_slam_face.mp4" },
    "minigames":  { "casino_showdown": "minigames/casino_showdown/index.html" }
  }
}
```

| 脚本指令 | 映射路径 |
|---|---|
| `@bg <name>` | `assets.bg.<name>` |
| `@<char> <look>` | `assets.characters.<char>.<look>` |
| `@music <name>` | `assets.music.<name>` |
| `@sfx <name>` | `assets.sfx.<name>` |
| `@cg <name> "..."` | `assets.cg.<name>`（扩展名由所选生产形态决定） |
| `@minigame <name> "..."` | `assets.minigames.<name>` |
| `@trick ...` | 无素材（引擎原生） |

映射表中找不到的语义名会产生 warning；编译产物可能缺少对应 `url`。
完整素材映射是发布前置条件，未解析完成的产物不是合格的发布 JSON。

---

## 6. 编译

Go 单二进制工具 `lsc`：

```bash
lsc compile 01.ls --assets mapping.json -o ep01.json   # 单集编译
lsc compile main/ --assets mapping.json -o novel.json   # 批量编译目录
lsc validate 01.ls --assets mapping.json                # 只验证不输出
lsc decompile ep01.json                                 # 从 JSON 反推 .ls + 映射表
```

职责：解析为 AST → 校验（语法、保留字、signal 命名）→ 素材映射 → 输出前端播放器
直接消费的结构化 JSON。**编译产物的字段定义见 `docs/JSON-OUTPUT.md`**，本文件不展开；
只需知道：step 带稳定 id、角色名统一小写、条件是结构化 AST 不含表达式字符串。

---

## 附录 A：指令速查表

| 指令 | 说明 |
|---|---|
| `@episode <bk>:<seq> "<title>" { }` | 集定义（文件根块） |
| `@gate { }` | 路由声明（每集必填且唯一） |
| `@if (<cond>): @next <bk>:<seq>` | gate 内跳转分支 |
| `@if (<cond>): @end <type>` | gate 内终结分支（`complete`/`to_be_continued`/`bad_ending`） |
| `@else @if (<cond>): ...` / `@else: ...` | gate 内链式/兜底分支 |
| `@pause` | 等玩家点击一次（无参数） |
| `@<char> <look> [transition]` | 角色显示/换 look（首次=入场） |
| `@<char> bubble <type>` | 气泡动画（9 种 type） |
| `@bg <name> [transition]` | 切背景（dissolve/fade/cut/slow） |
| `@cg <name> "<content>"` | 全屏 CG（叶子指令） |
| `CHARACTER: text` | 对白（自动显示说话角色） |
| `CHARACTER [look]: text` | 对白糖（= `@character look` + 对白） |
| `NARRATOR: text` | 旁白（清空所有立绘） |
| `YOU: text` | MC 内心独白（显示 MC 立绘） |
| `@phone {` ... `}` | 手机界面（必须多行；块内只许 `@text`；不配音） |
| `@text from/to <char>: content` | 收到/发出消息 |
| `@music <name>` / `@music stop` | 播放/停止 BGM |
| `@sfx <name>` | 一次性音效 |
| `@trick <type> "<prompt>"` | 强制体感交互（6 种 type） |
| `@minigame <name> "<desc>"` | 可选小游戏（叶子指令） |
| `@choice { }` / `@option <ID> <brave\|safe> "<text>" { }` | 选择块/选项；brave 必含 `check { }` |
| `check { attr / dc }` | 检定参数（attr 非空，dc 为正整数） |
| `@affection <char> <+/-N>` | 好感度变化（正负都合法） |
| `@signal mark <EVENT>` | 持久布尔标记（全大写） |
| `@signal int <NAME> (=\|+\|-) <int>` | 持久整数变量（全大写） |
| `@achievement <ID> { name/rarity/description }` | 成就解锁（ID 全大写格式，三字段必填） |
| `@butterfly "<desc>"` | 蝴蝶效应记录（不参与路由） |
| `@if (<cond>) { } @else @if / @else` | body 条件分支 |
| `MAX(...)` / `MIN(...)` | comparison 聚合 operand（≥2 参数） |
| `&<指令>` | 并发前缀（不可用于块结构指令） |

## 附录 B：保留字

| 标识符类型 | 保留字 |
|---|---|
| signal mark / signal int | `MAX`、`MIN` |
| look | `bubble` |

## 附录 C：最小完整示例

```
@episode main:01 "Three Place Settings" {

  // ===== 开场 =====
  @bg voss_house_kitchen_evening fade
  &music grief_suspense

  NARRATOR: Three place settings. Nobody set a fourth.

  @seren seren__urban_arrival__guarded
  YOU: They knew I was coming.

  @phone {
    @text from JAKE: Landed yet? Call me.
  }

  DEAN [dean__winter_fireside__tight_lipped]: You're late.

  @choice {
    @option A brave "Hold his stare." {
      check {
        attr: BOLD
        dc: 12
      }
      @if (check.success) {
        @signal mark STARED_DOWN_DEAN_EP01
        DEAN [dean__winter_fireside__deadpan]: ...Sit.
        @affection dean +2
        @butterfly "Met Dean's stare on the first night"
      } @else {
        @seren seren__urban_arrival__startled
        YOU: I blinked first.
        @butterfly "Tried to stare Dean down but flinched"
      }
    }
    @option B safe "Look away and sit." {
      @seren seren__urban_arrival__downcast
      YOU: Not tonight. Not my first hour here.
      @signal int TIMES_YIELDED +1
      @butterfly "Avoided confrontation with Dean on arrival"
    }
  }

  @sfx door_slam
  @seren seren__urban_arrival__hollow_stare
  YOU: Welcome home, I guess.

  @gate {
    @if (A.fail): @next main/bad/001:01
    @else: @next main:02
  }
}
```

## 附录 D：3.0.0 与旧版的差异

**移出本文件、归 skill 层的创作建议**：

- look 的 canonical 命名细则与 `look_vocab.json` 词表 → episode-writer skill
- CG 写作规范（分镜式、内嵌标签、道具独立成句、视频形态精修流程）→ episode-writer skill
- `check` 属性集合（如 BOLD/SWEET/SMART）与 dc 档位 → entity-planner skill
- mark 使用纪律（"必须有 reader"的写-读配对方法）→ planner / writer skill
- butterfly 文本写作要求 → skill
- trick 选型原则与权限论证 → 设计文档
- 定稿发布路径契约（`ep_<N>_final.ls`、`scripts/` 平铺）→ ide 发布相关 skill/docs
- 附录 A 的 120 行完整剧本 → 换成附录 C 最小示例

**语法层修正**：

- 背景切换的 canonical 形式改为 `@bg <name> [transition]`；`@bg set ...` 仅作存量脚本兼容
- `@phone` 补"必须多行"与"块内不配音"两条语义
- `@choice` 直接子节点只能是 `@option`，且至少两个
- `check.attr` 必须非空，`check.dc` 必须为正整数
- achievement ID 必须匹配 `^[A-Z][A-Z0-9_]*$`
- 检定属性不再可在 `@if` 中裸名读取（v1 示例中 `CHA >= 14` 的写法废止）；`@if` 裸名只解析作者 signal 与引擎数值
- 示例全部改用 canonical look 命名与全大写 signal

**删除的内容**：

- Dramatizer / Remix Executor 相关概念与整个"Remix 兼容"章节
- 文件结构中的 `remix/<session_id>/` 路径
- 解释器 JSON 输出的字段细节（指向 `docs/JSON-OUTPUT.md`）
