# 定時タスク用 prompt（v2）

以下を routine の prompt にそのまま貼る。routine の実行環境は **Network access = Full** の環境を指定すること
（Trusted のままだと一次情報源のほぼ全てが 403 になり、検索要約だけの簡報に戻る）。

---

生成一份「AI最新动向简报」。所有输出用日文。

## 0. 先读规范
- 仓库根目录 `CLAUDE.md`（发布机制、文件规约）。
- `docs/briefing-design.md`（编辑方针：读者三视角、收录/排除基准、政策门槛、四层信息收集、打分规则、输出结构）。本 prompt 与其冲突时以该文档为准。

## 1. 收集（四层，按顺序）
1. 运行 `python3 scripts/collect.py --hours 48 --out <scratchpad>/collected.md`，通读输出。失败的 feed 记下来，最后在报告里提一句。
2. 对 `sources.json` 的 `pages` 用 WebFetch 逐一查看（GitHub Trending、各 changelog、IPA/個人情報保護委員会/総務省、各社 customers 页、DORA 等）。
3. 用 WebSearch 做主题探针（见设计文档第 4 节的主题清单，至少 8 次，覆盖 DEV/CONSULT/PM 三视角，其中至少 3 次用日语针对日本国内）。
4. 读 `candidates.json`：对每个 status 为 seed/candidate/watching 的对象，搜一次有无新动态；同时把本次收集中新出现的产品/概念名加入候选池。

## 2. 选题
- 对所有候选按设计文档第 4 节打分，合计 ≥5 的进入收录候选；再过一遍 3.2 的排除项和 3.3 的政策门槛。
- 每条必须打开一次信息源确认正文和日期（48h 内）。打不开的不收。
- 与 `seen.json` 重复的不收。
- 目标 3–6 条，最多 8 条。没有够格的内容时，不凑数：改为对候选池中一个关注对象做深读（解决什么问题／怎么用／与替代方案的比较），并在报头说明当日无重大动态。

## 3. 输出
生成**一个完整的 HTML 文件** `outputs/ai-briefing-YYYY-MM-DD.html`（日期用 bash `date` 确认，JST）。Light mode，CSS 内联，字号偏大。沿用上一期的样式。
- 报头：日期。不要"本日のサマリー"。
- 每条：见出し 1 句／本文 200–300 字／出典（一次信息源，可点击）／视角标签（DEV / CONSULT / PM，可多选）＋每个视角一句「So what」／重要度（高＝今すぐ試せる・対応が要る，附一行怎么试或怎么应对；中＝追踪；低＝了解）／编辑评论 1 句。
- 高→中→低排序，颜色区分。
- 末尾「候補プールの動き」1–3 行（新规、晋升、退出）。
- 不要拆分文件；写完确认以 `</html>` 结尾。
- 更新 `index.html`（最上面加当天条目，href 为 `outputs/ai-briefing-YYYY-MM-DD.html`，核对文件存在）。
- 更新 `seen.json`（本次收录的事象）和 `candidates.json`（mentions / last_seen / sources / status）。

## 4. 发布与通知
- 按 `CLAUDE.md`：提交到工作分支并推送，再推送到 `main`，用 `git ls-tree -r --name-only origin/main | grep ai-briefing-$(date +%F)` 确认。
- 用 present_files 展示 HTML。
- Slack（Channel C0B967UK4AJ）发消息：
  ```
  :robot_face: AI最新動向簡報 YYYY年M月D日号 を公開しました。

  本日のハイライト：
  - （每条一行，不分重要度，行首可加 [DEV]/[CONSULT]/[PM]）

  簡報リンク：
  <https://alphakt.github.io/news/outputs/ai-briefing-YYYY-MM-DD.html|YYYY年M月D日号>
  <https://alphakt.github.io/news/|News一覧>
  ```
