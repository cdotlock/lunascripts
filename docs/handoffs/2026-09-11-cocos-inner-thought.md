# Cocos 客户端 INNER_THOUGHT 迁移交接

日期：2026-09-11。状态：交由客户端同事实施；本次未修改 Cocos 源码。

## 目标

LunaScript 4.0.0 的创作语法为 `INNER_THOUGHT:`，编译器输出 `type: "inner_thought"`。客户端同时读取新的 `inner_thought` 与历史 `you`，保持原内心独白的 MC 立绘、文本、推进、存档及既有音频行为。所有创作指导只使用新名字，不教旧别名。

**不要重写已发布内容，不要重新编号步骤。** JSON 字段改名，但步骤 ID 继续使用原 `you` 后缀，例如 `0002_you`；这与存档 cursor 有关。`char_show.character: "you"` 的既有 MC 占位身份也不变。

## 源码与具体入口

- 本地：`/Users/Clock/lunaverse/lunaverse-cocos-client`
- 远端：https://github.com/Rydia-China/moonshort
- 在 `assets/bundles/app/` 下搜索 `you` 的类型与分支，已确认至少包括：
  - `ls/LsTypes.ts`：步骤联合类型。
  - `ls/StoryFrameNormalizer.ts`：JSON 转运行时 frame。
  - `ls/story-render/DialogueRenderer.ts`：独白渲染与 MC 身份。
  - `ls/story-render/StoryFrameDispatcher.ts`：frame 分发。
  - `ls/StepPlayer.ts`：执行与推进。
  - `ls/story-render/StoryRenderContext.ts`：渲染上下文。
  - `assets/bundles/play/story/StoryWnd.ts`：播放窗口（不在 app 目录内）。
  - `core/StageRuntime.ts`：舞台状态。
  - `core/AppRenderer.ts` 与 `api/ApiTypes.ts`：响应适配及 API 类型。

推荐在现有解析/归一化边界接入新类型，复用原独白逻辑；如果保留两种运行时 discriminator，所有相关 switch、集合与类型收窄必须同时覆盖。

## 输入样例

新格式（4.0.0）：

```json
{
  "ls_contract_version": "4.0.0",
  "episode_id": "main:01",
  "branch_key": "main",
  "seq": 1,
  "title": "Private thought",
  "steps": [
    {"id": "0001_you", "type": "inner_thought", "text": "No one heard that."}
  ],
  "gate": {"next": "main:02"},
  "ending": null
}
```

旧格式同一段内容使用 `ls_contract_version: "3.0.0"` 与 `type: "you"`，应正常播放。历史未版本化 JSON 也保持现有支持。

## 验收

1. 新旧 JSON 的独白都被识别为 MC 内心独白，不成为名叫 INNER_THOUGHT 的普通角色。
2. 展示、立绘继承、点击/自动推进与旧行为一致；不改变该客户端既有音频策略。
3. 普通序列、选项体、条件分支及现有嵌套结构中的新节点可执行。
4. 原步骤 ID 不变，历史游标恢复正常。
5. 同一场景中真实角色对白、NARRATOR 与 INNER_THOUGHT 不混淆。
6. 不只测接口：实际播放新格式及一份旧格式样例，交付测试结果与对应源码版本。

## 产物交付与上线依赖

外部客户端通过 `jsonUrl` 直接从 CDN 取 Episode JSON，Backend 双读不会替客户端转换数据。因此新内容发布前必须完成客户端支持；已安装旧版本不能仅靠服务端更新获得新类型支持。

Standalone：按仓库流程运行 `npm run build:standalone-play`，交付完整 `build/standalone-play` 目录、`standalone-release.json`、源码提交和验收结果。供 IDE 接收的目录是 `packages/ls-preview/media/cocos-player/`，来源记录为 `packages/ls-preview/media/cocos-player-source.md`。保留官方构建产物原文，不直接手改生成的 JS。

原生端：本次涉及 app bundle 的解析与运行时，仅发布 play bundle 不足；按客户端正常流程发布匹配的 app bundle/整包，并明确已发布客户端的支持范围。

IDE 这次另有宿主输入适配，可向旧嵌入式播放器传入兼容副本；它仅保护 IDE 内嵌预览，不能代替外部 Cocos 客户端升级。

关联 PR：Lunascripts https://github.com/cdotlock/lunascripts/pull/7；Backend https://github.com/cdotlock/lunaverse-backend/pull/276；IDE https://github.com/MobAI-Inc/lunaverse-ide/pull/4；IDE Cloud https://github.com/cdotlock/lunaverse-ide-cloud/pull/59。
