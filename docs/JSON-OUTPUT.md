# LS JSON 输出参考手册

> 供前端播放器/游戏引擎对接使用。本文只定义 `lsc compile` 输出的 JSON wire format，不定义前端呈现策略。

---

## 1. 顶层结构

```json
{
  "ls_contract_version": "4.0.0",
  "episode_id": "main:01",
  "branch_key": "main",
  "seq": 1,
  "title": "Butterfly",
  "steps": [ ... ],
  "gate": { ... } | null,
  "ending": { ... } | null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ls_contract_version` | string | 生成该 JSON 的 Lunaverse Script 契约版本；当前固定为 `"4.0.0"` |
| `episode_id` | string | 集的完整标识，格式 `<branch_key>:<seq>`，如 `"main:01"` |
| `branch_key` | string | 分支路径，如 `"main"`、`"main/bad/001"`、`"remix/abc123"` |
| `seq` | number | 集序号（从 1 开始） |
| `title` | string | 集标题 |
| `steps` | array | 步骤数组（混合类型，见下文） |
| `gate` | object\|null | 路由规则（嵌套 if/else 链）。详见 §6 |
| `ending` | object\|null | 终结标记。详见 §7 |

### 1.1 gate / ending 的取舍

编译器根据 LS 源 `@gate { ... }` 块的内容决定填哪个字段：

- **纯无条件终结** `@gate { @end TYPE }` → `gate: null, ending: {type: TYPE}`
- **其他所有情形**——纯无条件 `@next`、条件路由、`@end`/`@next` 混合——→ `gate: <AST>, ending: null`

`ending` 字段为顶层简单形态，保留是为了与现有 overlay 系统平滑过渡。条件终结、`@end` 与 `@next` 混合的路由全部在 gate AST 内部表达（叶子节点可以是 `{next: ...}` 或 `{end: ...}`）。

成就是 inline step，不再出现在顶层字段——每个 `achievement` step 自带完整元数据，详见 §4.7。

---

## 2. Steps 数组：混合类型

`steps` 数组包含两种元素类型：

```
steps: [
  { ... },          // 对象 → 单步骤
  [ {...}, {...} ], // 数组 → 并发组
  { ... },          // 对象 → 单步骤
  ...
]
```

### 2.1 单步骤（对象）

一个普通的 JSON 对象，代表一条独立指令。引擎按顺序执行。

```json
{
  "type": "narrator",
  "text": "Senior year. Day one."
}
```

### 2.2 并发组（数组）

一个 JSON 数组，包含多个步骤对象。引擎**同时执行**组内所有步骤。

```json
[
  {
    "type": "bg",
    "name": "school_hallway",
    "url": "https://oss.mobai.com/.../school_hallway.png",
    "transition": "fade"
  },
  {
    "type": "music",
    "name": "tense_strings",
    "url": "https://oss.mobai.com/.../tense_strings.mp3"
  },
  {
    "type": "char_show",
    "character": "mauricio",
    "look": "neutral_smirk"
  }
]
```

### 2.3 分组规则

并发组由 LS 脚本中的 `@`（领导者）和 `&`（跟随者）前缀决定：

- `@` 指令开启新的步骤组
- `&` 指令加入前一个步骤组
- 对话行（dialogue / narrator / inner_thought）始终独立
- 只有一条指令的组自动展平为对象，不包裹数组

| LS 脚本 | JSON 输出 |
|----------|----------|
| `@bg ...` 单独 | `{ "type": "bg", ... }` 对象 |
| `@bg ...` + `&music ...` + `&<char> <pose>` | `[{"type":"bg"}, {"type":"music"}, {"type":"char_show"}]` 数组 |
| `NARRATOR: text` | `{ "type": "narrator", ... }` 对象（始终独立） |

---

## 3. 文档边界

本文仅规定字段与嵌套形态。角色可见性、立绘切换、清屏、动画与交互推进策略不属于 JSON wire contract。

发布有效的 JSON 中，素材类 URL 必须完成解析。编译器可对缺失素材发出 warning 并产出 URL 缺失或为空的中间结果，但该结果不满足发布契约。

---

## 4. 步骤类型完整参考

### 4.0 Step ID（稳定步骤标识）

加在所有 step 上的 `id` 字段是后端 player cursor 的稳定锚点。这是**冻结契约**——一旦 episode JSON 发到带持久 session 的后端，编译器对 id 的算法就不能再变（除非配套数据迁移）。

#### 字段形态

每个 step 都有一个必填的 `id: string` 字段，格式 `<seq>_<tag>`，两段由下划线分隔。

```json
{
  "id": "0003_dlg",
  "type": "dialogue",
  "character": "easton",
  "text": "Can I sit?"
}
```

#### `<tag>` 段：类型缩写

`<tag>` 是 2-4 个小写字母，由 step 的 `type` 决定。一种 tag 可对应多个 step type（视觉/音频类按"组"归并）。

| step type | tag |
|-----------|-----|
| `dialogue` | `dlg` |
| `narrator` | `nar` |
| `inner_thought` | `you` |
| `pause` | `pau` |
| `choice` | `ch` |
| `minigame` | `mg` |
| `trick` | `trk` |
| `cg_show` | `cg` |
| `bg` | `bg` |
| `char_show` / `bubble` | `char` |
| `music` / `music_stop` | `mus` |
| `sfx` | `sfx` |
| `phone_show` / `text_message` | `phn` |
| `signal` | `sig` |
| `affection` | `aff` |
| `achievement` | `ach` |
| `butterfly` | `btf` |
| `if` | `ctrl` |

#### `<seq>` 段：4 位 0-padded 计数器，**Episode 全局作用域**

`<seq>` 是 4 位零填充的 1-based 整数。整个 episode 树共享一个单调递增计数器，按 DFS 前序遍历分配——**不在任何容器边界重置**。

子容器（`choice.options[i].steps`、`if.then`/`if.else`、`phone_show.messages`）的子步骤在父步骤被编号之后继续递增。`minigame`、`trick`、`cg_show` 都是 leaf step——它们各自消耗一个 seq，但**不开 child counter**，下一个兄弟步骤直接在父容器的计数器里继续。

**并发组**：LS 的 `&` 跟随节点会和 `@` 领导节点合并成一个 JSON 数组（见 §2.2），组内成员在同一个计数器里**继续递增**。

**嵌套 `@else @if`**：嵌套的 IfStep 本身不分配 id，只有其 `then`/`else` 子步骤使用共享计数器。

#### 例子

```
顶层 episode.steps:
  0001_dlg, 0002_nar, [0003_char, 0004_char], 0005_ch, 0014_dlg, 0015_dlg
                       ^^^^^^^^^^^^^^^^^^^^^^^^
                       并发组 — 计数器持续递增

steps[4] = 0005_ch choice 的 options[0].steps（Brave 选项 A）:
  0006_dlg, 0007_nar, 0008_dlg
  ^^^^^^^^
  从 choice 的 0005 之后继续递增
```

#### 唯一性

同一份 JSON 中**不会出现重复 id**——`sort(allStepIDs) == DFS 声明顺序`。后端 player cursor 既可以用 id 直接定位（全局唯一），也可以用完整路径定位。路径形式示例：

```
["0005_ch", "options", "A", "steps", "0006_dlg"]
```

#### 冻结契约

编译器内部的 `assignStepID` + `stepTypeTag` 函数（在 `internal/emitter/emitter.go`）是 step id 的**唯一权威**。一旦 episode JSON 已经发到带持久 player session 的后端：

- **不可改 tag**
- **不可改 seq 宽度**
- **不可改遍历顺序**
- **不可改起始值**

任何上述变更都会让所有持久化的 cursor 指错位置。如果实在要改，必须配套写一次性 cursor migration。

> **注意：** 本文剩余 §4.x 类型表中省略 `id` 字段以聚焦各类型自身字段。请把 `id: string` 当作所有 step 的隐式必填字段。

### 4.1 视觉类

#### `bg` — 背景切换

```json
{
  "type": "bg",
  "name": "school_hallway",
  "url": "https://oss.mobai.com/.../school_hallway.png",
  "transition": "fade"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 素材语义名 |
| `url` | string | 是 | 已解析的 OSS URL |
| `transition` | string | 否 | `"dissolve"` / `"fade"` / `"cut"` / `"slow"` |

#### `char_show` — 角色显示 / 换 pose

`char_show` 不输出 `position` 字段。

```json
{
  "type": "char_show",
  "character": "mauricio",
  "look": "neutral_smirk",
  "url": "https://oss.mobai.com/.../mauricio_neutral_smirk.png",
  "transition": "dissolve"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `character` | string | 是 | 角色 ID（小写） |
| `look` | string | 是 | 立绘名 |
| `url` | string | 是 | 已解析的 OSS URL |
| `transition` | string | 否 | `"dissolve"` / `"fade"` / `"cut"` / `"slow"` |

#### `bubble` — 气泡动画

```json
{
  "type": "bubble",
  "character": "josie",
  "bubble_type": "heart"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `character` | string | 是 | 角色 ID |
| `bubble_type` | string | 是 | `"anger"` / `"sweat"` / `"heart"` / `"question"` / `"exclaim"` / `"idea"` / `"music"` / `"doom"` / `"ellipsis"` |

#### `cg_show` — CG 展示（leaf）

CG 步骤携带素材语义名、解析后 URL 与生成所需的叙事 prose。

```json
{
  "type": "cg_show",
  "name": "window_stare",
  "url": "https://oss.mobai.com/.../window_stare.mp4",
  "content": "The camera opens on Malia's silhouette against the rain-streaked window. Slow push-in on her eyes — one tear tracks down, catching the cold blue of the skyline. Her reflection doubles her, ghost-like, in the glass."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | CG 素材语义名 |
| `url` | string | 是 | 已解析的 OSS URL；中间编译结果可为空，但不满足发布契约 |
| `content` | string | **是** | 英文连续叙述：镜头走向 + 故事情节 |

**leaf step**——无 `steps` 子数组、无 `duration`、无 `transition` 字段。

### 4.2 对话类

#### `dialogue` — 角色对白

```json
{
  "type": "dialogue",
  "character": "mauricio",
  "text": "Hey, Butterfly."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `character` | string | 是 | 角色 ID（**始终小写**，脚本中 `MAURICIO:` → JSON 中 `"mauricio"`） |
| `text` | string | 是 | 对白内容 |

> **注意：** 所有步骤类型中的 `character` 字段在 JSON 输出中统一为小写。

#### `narrator` — 旁白

```json
{
  "type": "narrator",
  "text": "Senior year. Day one."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | 是 | 旁白内容 |

#### `inner_thought` — 内心独白

```json
{
  "type": "inner_thought",
  "text": "Another year. Same mess."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | 是 | MC 内心独白内容 |

### 4.3 时序控制类

#### `pause` — 暂停等待

```json
{
  "type": "pause"
}
```

无额外字段。

### 4.4 手机/消息类

#### `phone_show` — 手机界面

```json
{
  "type": "phone_show",
  "messages": [
    {"type": "text_message", "direction": "from", "character": "easton", "text": "Can we talk?"},
    {"type": "text_message", "direction": "to", "character": "mauricio", "text": "How do you know?"}
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `messages` | array | 是 | `text_message` 对象列表 |

#### `text_message` — 短信消息（phone_show 内部）

```json
{
  "type": "text_message",
  "direction": "from",
  "character": "easton",
  "text": "Can we talk? I miss you."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `direction` | string | 是 | `"from"`（`character` 为发件人）/ `"to"`（`character` 为收件人） |
| `character` | string | 是 | 角色 ID（小写） |
| `text` | string | 是 | 消息内容 |

### 4.5 音频类

#### `music` — 播放 BGM

```json
{
  "type": "music",
  "name": "calm_morning",
  "url": "https://oss.mobai.com/.../calm_morning.mp3"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 曲目语义名 |
| `url` | string | 是 | 已解析的 OSS URL |

#### `music_stop` — 停止 BGM

```json
{
  "type": "music_stop"
}
```

无额外字段。

#### `sfx` — 一次性音效

```json
{
  "type": "sfx",
  "name": "door_slam",
  "url": "https://oss.mobai.com/.../door_slam.mp3"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 音效语义名 |
| `url` | string | 是 | 已解析的 OSS URL |

### 4.6 游戏机制类

#### `choice` — 选择菜单

brave 和 safe 选项内容统一在 `steps` 字段下。brave 的成功/失败分支通过嵌套的 `@if (check.success) { } @else { }` step 表达（`check` condition type）。

```json
{
  "type": "choice",
  "options": [
    {
      "id": "A",
      "mode": "brave",
      "text": "Stand your ground.",
      "check": { "attr": "CHA", "dc": 12 },
      "steps": [
        {
          "type": "if",
          "condition": {"type": "check", "result": "success"},
          "then": [ ... ],
          "else": [ ... ]
        }
      ]
    },
    {
      "id": "B",
      "mode": "safe",
      "text": "Have Mark make a scene.",
      "steps": [ ... ]
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `options` | array | 是 | 选项列表，至少 2 项 |

**Option 对象：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 选项编号（A / B / C ...） |
| `mode` | string | 是 | `"brave"`（需检定）/ `"safe"`（无检定） |
| `text` | string | 是 | 选项显示文本 |
| `check` | object | brave 必填 | `{ "attr": "CHA", "dc": 12 }`；`attr` 非空，`dc` 为正整数 |
| `steps` | array | 是 | 选项体内所有步骤 |

#### `minigame` — 可选小游戏（leaf）

`minigame` 是 leaf step，没有 body / steps / 评级分支。`description` 用于下游生成，`game_url` 携带解析后素材地址。

```json
{
  "type": "minigame",
  "name": "qte_challenge",
  "game_url": "https://oss.mobai.com/.../qte_challenge/index.html",
  "description": "Mr. Chen pairs Malia and Mauricio for the opening reading exercise..."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 素材句柄，用于查 `assets.minigames.<name>` |
| `game_url` | string | 否 | 已解析的小游戏 URL。生成器尚未完成时可缺省或为空字符串 |
| `description` | string | **是** | 连贯英文 prose：场景 + 简单玩法 |

#### `trick` — 强制 trick（leaf）

`trick` 是 leaf step，无子步骤、奖励、评级或叙事分支。

```json
{
  "type": "trick",
  "trick_type": "hold",
  "prompt": "Hold your breath until he walks past."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `trick_type` | string | 是 | 6 个锁定值之一：`tap` / `hold` / `swipe` / `shake` / `swing` / `tilt`。其它值是 parser/validator error |
| `prompt` | string | 是 | 一行祈使，给玩家看。不可为空串 |

阈值（点几下、按多久等）由引擎内置，**脚本不传**。所有 6 个类型都不需要摄像头 / 麦克风权限。

### 4.7 状态变更类

#### `affection` — 好感度

```json
{ "type": "affection", "character": "easton", "delta": 2 }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `character` | string | 是 | 角色 ID（小写） |
| `delta` | number | 是 | 增减值（可正可负） |

#### `signal` — 持久信号

```json
{ "type": "signal", "kind": "mark", "event": "EP01_COMPLETE" }
{ "type": "signal", "kind": "int", "name": "REJECTIONS", "op": "+", "value": 1 }
{ "type": "signal", "kind": "int", "name": "REJECTIONS", "op": "=", "value": 0 }
```

按 `kind` 分派字段：

**mark**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `kind` | string | 是 | `"mark"` |
| `event` | string | 是 | 事件名（SCREAMING_SNAKE_CASE 英文） |

**int**：

`name` 与 `mark.event` 使用同一作者命名规则：必须匹配
`^[A-Z][A-Z0-9_]*$`。小写裸名留给运行时声明的只读引擎数值。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `kind` | string | 是 | `"int"` |
| `name` | string | 是 | 作者变量名（`SCREAMING_SNAKE_CASE`，匹配 `^[A-Z][A-Z0-9_]*$`） |
| `op` | string | 是 | `"="` / `"+"` / `"-"` |
| `value` | number | 是 | 整数。op=`=` 时可为负；op=`+`/`-` 时为非负 |

#### `achievement` — 成就解锁

```json
{
  "type": "achievement",
  "achievement_id": "HIGH_HEEL_DOUBLE_KILL",
  "name": "Heel Twice Over",
  "rarity": "epic",
  "description": "Once is improvisation. Twice is a signature move."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `achievement_id` | string | 是 | 成就语义标识，匹配 `^[A-Z][A-Z0-9_]*$` |
| `name` | string | 是 | 显示名称（英文） |
| `rarity` | string | 是 | `"uncommon"` / `"rare"` / `"epic"` / `"legendary"`（**无 `common`**） |
| `description` | string | 是 | DM 口吻 flavor 文本（英文） |

> **注意 `id` vs `achievement_id`：** `id` 是通用 cursor 步骤标识（`<seq>_ach`）；`achievement_id` 是 LS 源中的成就语义标识。

#### `butterfly` — 蝴蝶效应记录

```json
{ "type": "butterfly", "description": "Accepted Easton's approach at the cafeteria" }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `description` | string | 是 | 英文 prose：玩家行为与其性格含义 |

`butterfly` 是下游内容生成元数据，不参与 gate 路由。

### 4.8 流程控制类

#### `if` — 条件分支

条件为**完全结构化的 AST 对象**（不含表达式字符串），后端可直接遍历判定。`else` 可以是步骤数组（简单 else）或嵌套的 `if` 对象（`@else @if` 链）。

```json
{
  "type": "if",
  "condition": {
    "type": "compound",
    "op": "&&",
    "left":  {"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 5}},
    "right": {"type": "comparison", "left": {"kind": "value", "name": "CHA"}, "op": ">=", "right": {"kind": "literal", "value": 14}}
  },
  "then": [ ... ],
  "else": {
    "type": "if",
    "condition": {"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 3}},
    "then": [ ... ],
    "else": [ ... ]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `condition` | object | 是 | 结构化条件 AST（见条件类型参考） |
| `then` | array | 是 | 条件成立时执行的步骤 |
| `else` | array\|object | 否 | 步骤数组（简单 `@else { }` → `[...]`）或裸 `if` 对象（`@else @if` 链 → `{"type": "if", ...}`） |

#### 条件类型参考

条件对象包含 `type` 字段和类型特有字段。**所有条件字段都是结构化的，不含表达式字符串**。

**`choice`** — 选项检定结果

```json
{"type": "choice", "option": "A", "result": "fail"}
```

| 字段 | 取值 |
|------|------|
| `option` | 选项 ID（`"A"` / `"B"` / ...） |
| `result` | `"success"` / `"fail"` / `"any"` |

**`flag`** — 信号布尔标记

```json
{"type": "flag", "name": "EP01_COMPLETE"}
```

**`comparison`** — 数值比较。左右两侧都是 operand AST：

```json
// 变量与字面量
{"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 5}}

// 变量与变量
{"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">", "right": {"kind": "affection", "char": "diego"}}

// 引擎/作者变量
{"type": "comparison", "left": {"kind": "value", "name": "san"}, "op": "<=", "right": {"kind": "literal", "value": 20}}

// 聚合 operand
{"type": "comparison", "left": {"kind": "max", "args": [
  {"kind": "affection", "char": "easton"},
  {"kind": "affection", "char": "diego"}
]}, "op": ">=", "right": {"kind": "literal", "value": 5}}
```

| 字段 | 说明 |
|------|------|
| `left` | Operand AST（见 operand 类型） |
| `op` | `">="` / `"<="` / `">"` / `"<"` / `"=="` / `"!="` |
| `right` | Operand AST（见 operand 类型） |

#### Operand 类型

`comparison.left` 和 `comparison.right` 都是 operand AST，包含 `kind` 字段。**5 种 kind**：`literal` / `affection` / `value` / `max` / `min`。

**`literal`** — 整数字面量

```json
{"kind": "literal", "value": 5}
{"kind": "literal", "value": -2}
```

**`affection`** — 角色好感度

```json
{"kind": "affection", "char": "easton"}
```

| 字段 | 说明 |
|------|------|
| `char` | 角色 ID（小写） |

**`value`** — 裸名数值（引擎管理数值或作者 `@signal int` 变量）

```json
{"kind": "value", "name": "san"}
{"kind": "value", "name": "REJECTIONS"}
```

| 字段 | 说明 |
|------|------|
| `name` | 数值名。引擎在自己的数值存储和 signal int 存储中按裸名查找（共享命名空间） |

**`max` / `min`** — 聚合 operand

求 args 列表中所有 operand 的最大值（`max`）或最小值（`min`）。args 数量**任意 ≥ 2**，没有上限——可以聚合两个、三个、四个甚至更多 operand。

```json
// 2 args
{
  "kind": "max",
  "args": [
    {"kind": "affection", "char": "easton"},
    {"kind": "affection", "char": "diego"}
  ]
}

// 4 args（4 个 LI 的最高好感度）
{
  "kind": "max",
  "args": [
    {"kind": "affection", "char": "easton"},
    {"kind": "affection", "char": "diego"},
    {"kind": "affection", "char": "mauricio"},
    {"kind": "affection", "char": "elias"}
  ]
}

// 混合 operand kind
{
  "kind": "min",
  "args": [
    {"kind": "affection", "char": "easton"},
    {"kind": "value", "name": "REJECTIONS"},
    {"kind": "literal", "value": 10}
  ]
}

// 递归嵌套（不鼓励但合法）
{
  "kind": "max",
  "args": [
    {"kind": "affection", "char": "easton"},
    {"kind": "min", "args": [
      {"kind": "affection", "char": "diego"},
      {"kind": "affection", "char": "mauricio"}
    ]}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `args` | Operand AST 数组。**长度 ≥ 2，无上限**。每个 arg 可以是任意 kind（含递归嵌套的 max/min） |

**`compound`** — 复合条件。`left` 和 `right` 是递归的完整条件对象：

```json
{
  "type": "compound",
  "op": "&&",
  "left":  {"type": "flag", "name": "A"},
  "right": {"type": "comparison", "left": {"kind": "value", "name": "san"}, "op": "<=", "right": {"kind": "literal", "value": 20}}
}
```

| 字段 | 说明 |
|------|------|
| `op` | `"&&"` 或 `"\|\|"` |
| `left` | 左子条件（任意条件类型对象，支持递归嵌套） |
| `right` | 右子条件（任意条件类型对象，支持递归嵌套） |

**`check`** — brave option 检定结果条件（context-local）

```json
{"type": "check", "result": "success"}
```

| 字段 | 取值 |
|------|------|
| `result` | `"success"` / `"fail"` |

只在 brave option 体内的 `@if` 里生成。

---

## 5. 并发组形态

LS 源码：
```
@bg school_cafeteria fade
&music casual_lunch
&mark grin_confident
```

JSON 输出：
```json
[
  {"type": "bg", "name": "school_cafeteria", "url": "...", "transition": "fade"},
  {"type": "music", "name": "casual_lunch", "url": "..."},
  {"type": "char_show", "character": "mark", "look": "grin_confident", "url": "..."}
]
```

---

## 6. Gate 路由

`gate` 是集的路由声明，决定玩家完成本集后跳转到哪一集或如何终结。采用嵌套 if/else 链结构，条件为结构化对象，**叶子节点可以是 `{next: <branch_key>}` 或 `{end: <ending_type>}`**。

### 6.1 形态示例

**纯条件路由**：

```json
"gate": {
  "if": {"type": "choice", "option": "A", "result": "fail"},
  "next": "main/bad/001:01",
  "else": {
    "if": {"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 5}},
    "next": "main/route/001:01",
    "else": {"next": "main:02"}
  }
}
```

**条件终结 + 路由混合**：

```json
"gate": {
  "if": {"type": "comparison", "left": {"kind": "value", "name": "REJECTIONS"}, "op": ">=", "right": {"kind": "literal", "value": 3}},
  "end": "bad_ending",
  "else": {
    "if": {"type": "flag", "name": "HEROIC_END"},
    "end": "complete",
    "else": {"next": "main:02"}
  }
}
```

**无条件路由**：

```json
"gate": {"next": "main:02"}
```

### 6.2 判定规则

- 引擎按 if → else.if → else 链式判定
- 第一个命中的条件生效，使用对应的叶子动作
- 叶子动作有两种：`next` → 跳转到 branch_key；`end` → 显示终结画面（type 为 `complete` / `to_be_continued` / `bad_ending`）
- 最内层的 `else` 节点只有叶子动作字段（`next` 或 `end`），不再嵌套

### 6.3 Gate 节点结构

每个 gate 节点包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `if` | object | 否 | 结构化条件对象（最内层 else 兜底节点无此字段） |
| `next` | string | next 叶子必填 | 命中时跳转的目标 episode_id |
| `end` | string | end 叶子必填 | 命中时终结的类型（`complete` / `to_be_continued` / `bad_ending`）。与 `next` 互斥 |
| `else` | object | 否 | 下一个 gate 节点（嵌套 if/else） |

### 6.4 条件类型

Gate 中的条件使用与 body `@if` 相同的结构化 AST 格式（见 §4.8 条件类型参考），所有 4 种类型可用：`choice` / `flag` / `comparison` / `compound`。

**gate 中不会出现 `check` 条件**——它只在 brave option 体内的 body `@if` 里生成。

---

## 7. Ending 终结标记

`ending` 字段是简单形态的集终结声明——仅在 LS 源使用纯无条件 `@gate { @end TYPE }` 时由编译器填入：

```json
{
  "gate": null,
  "ending": {"type": "bad_ending"}
}
```

| type | 含义 |
|------|------|
| `complete` | 全剧终 |
| `to_be_continued` | 待续 |
| `bad_ending` | 坏结局 |

---

## 8. 完整 JSON 示例

以下示例展示了并发组、单步骤、暂停、选择、条件分支和路由的完整 JSON 输出：

```json
{
  "episode_id": "main:01",
  "branch_key": "main",
  "seq": 1,
  "title": "Butterfly",
  "steps": [
    [
      {
        "type": "bg",
        "name": "malias_bedroom_morning",
        "url": "https://oss.mobai.com/novel_001/bg/malias_bedroom_morning.png"
      },
      {
        "type": "music",
        "name": "calm_morning",
        "url": "https://oss.mobai.com/novel_001/music/calm_morning.mp3"
      },
      {
        "type": "char_show",
        "character": "malia",
        "look": "neutral_phone",
        "url": "https://oss.mobai.com/novel_001/characters/malia_neutral_phone.png"
      }
    ],
    {
      "type": "narrator",
      "text": "Senior year. Day one. Status: already complicated."
    },
    {
      "type": "inner_thought",
      "text": "Another year. Same mess."
    },
    {
      "type": "phone_show",
      "messages": [
        {"type": "text_message", "direction": "from", "character": "easton", "text": "Can we talk? I miss you."},
        {"type": "text_message", "direction": "from", "character": "easton", "text": "I know I messed up."}
      ]
    },
    {
      "type": "inner_thought",
      "text": "Eight months and he still won't stop."
    },
    {
      "type": "char_show",
      "character": "malia",
      "look": "worried",
      "url": "https://oss.mobai.com/novel_001/characters/malia_worried.png"
    },
    {
      "type": "pause"
    },
    {
      "type": "choice",
      "options": [
        {
          "id": "A",
          "mode": "brave",
          "text": "Let him come.",
          "check": {
            "attr": "CHA",
            "dc": 12
          },
          "steps": [
            {
              "type": "if",
              "condition": {"type": "check", "result": "success"},
              "then": [
                {"type": "signal", "kind": "mark", "event": "EASTON_APPROACHED_EP01"},
                {
                  "type": "char_show",
                  "character": "easton",
                  "look": "relieved",
                  "url": "https://oss.mobai.com/novel_001/characters/easton_relieved.png"
                },
                {"type": "dialogue", "character": "easton", "text": "Can I sit?"},
                {"type": "dialogue", "character": "malia", "text": "You have two minutes."},
                {"type": "affection", "character": "easton", "delta": 2},
                {"type": "signal", "kind": "int", "name": "EASTON_APPROACHES_ACCEPTED", "op": "+", "value": 1},
                {"type": "butterfly", "description": "Accepted Easton's approach at the cafeteria"}
              ],
              "else": [
                {
                  "type": "char_show",
                  "character": "easton",
                  "look": "hurt",
                  "url": "https://oss.mobai.com/novel_001/characters/easton_hurt.png"
                },
                {"type": "dialogue", "character": "malia", "text": "I... I can't do this."},
                {"type": "butterfly", "description": "Tried to face Easton but lost courage"}
              ]
            }
          ]
        },
        {
          "id": "B",
          "mode": "safe",
          "text": "Have Mark make a scene.",
          "steps": [
            {
              "type": "char_show",
              "character": "mark",
              "look": "grin_mischief",
              "url": "https://oss.mobai.com/novel_001/characters/mark_grin_mischief.png"
            },
            {"type": "dialogue", "character": "mark", "text": "HEY EASTON! You want some of my mystery casserole?"},
            {"type": "bubble", "character": "mark", "bubble_type": "music"},
            {"type": "inner_thought", "text": "Thank god for Mark."},
            {"type": "butterfly", "description": "Had Mark create a diversion to avoid Easton"}
          ]
        }
      ]
    },
    {
      "type": "if",
      "condition": {
        "type": "compound",
        "op": "&&",
        "left":  {"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 5}},
        "right": {"type": "comparison", "left": {"kind": "value", "name": "CHA"}, "op": ">=", "right": {"kind": "literal", "value": 14}}
      },
      "then": [
        {"type": "dialogue", "character": "easton", "text": "You remembered."}
      ],
      "else": [
        {"type": "dialogue", "character": "easton", "text": "...Hey."}
      ]
    },
    {"type": "signal", "kind": "mark", "event": "EP01_COMPLETE"}
  ],
  "gate": {
    "if": {"type": "choice", "option": "A", "result": "fail"},
    "next": "main/bad/001:01",
    "else": {
      "if": {"type": "comparison", "left": {"kind": "affection", "char": "easton"}, "op": ">=", "right": {"kind": "literal", "value": 3}},
      "next": "main/route/001:01",
      "else": {"next": "main:02"}
    }
  },
  "ending": null
}
```

### 8.1 终结集示例（纯无条件）

```json
{
  "episode_id": "main/bad/001:02",
  "branch_key": "main/bad/001",
  "seq": 2,
  "title": "Bad End",
  "steps": [
    {"type": "bg", "name": "malias_bedroom_night", "url": "..."},
    {"type": "narrator", "text": "She never came home."}
  ],
  "gate": null,
  "ending": {"type": "bad_ending"}
}
```

### 8.2 条件终结示例（gate 内含 end 叶子）

```json
{
  "episode_id": "main/route/redemption:03",
  "branch_key": "main/route/redemption",
  "seq": 3,
  "title": "The Final Choice",
  "steps": [ ... ],
  "gate": {
    "if": {"type": "flag", "name": "ALL_LIS_REJECTED"},
    "end": "bad_ending",
    "else": {
      "if": {"type": "comparison", "left": {"kind": "max", "args": [
        {"kind": "affection", "char": "easton"},
        {"kind": "affection", "char": "mauricio"},
        {"kind": "affection", "char": "elias"}
      ]}, "op": ">=", "right": {"kind": "literal", "value": 8}},
      "end": "complete",
      "else": {"next": "main/route/redemption:04"}
    }
  },
  "ending": null
}
```

---

## 9. 稀有度目标分布

设计剧情成就时的典型解锁率目标（参考值，非强制）：

| rarity | 典型解锁率 | 典型触发形态 |
|--------|-----------|-------------|
| `uncommon` | 20-40% | 单集戏剧性选择的其中一支 |
| `rare` | 5-20% | 反直觉选择、DC 14+ 检定、两集组合、失败路径 |
| `epic` | 1-5% | 3+ 集的行为模式 |
| `legendary` | <1% | 4+ 集的组合 + 特定检定结果 |
