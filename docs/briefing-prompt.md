# 定時タスク用 prompt（v2.1, 2026-10-06）

以下を routine の prompt にそのまま貼る。routine の実行環境は **Network access = Full** の環境を指定すること
（Trusted のままだと一次情報源のほぼ全てが 403 になり、検索要約だけの簡報に戻る）。

---

生成一份「AI最新动向简报」。所有输出用日文。

## 0. 先读规范
- 仓库根目录 `CLAUDE.md`（发布机制、文件规约）。
- `docs/briefing-design.md`（编辑方针与 token 预算）。本 prompt 与其冲突时以该文档为准。

## 1. 收集（只做这四步，不要额外 WebFetch）
1. 运行 `python3 scripts/collect.py --hours 48 --out <scratchpad>/collected.md`，**只读这一个文件**。它已包含：29 个 feed 的 48h 新条目（已排除 seen.json）、23 个无 feed 页面的新增链接（"変化なし"的页面不要再去打开）。
2. WebFetch 恰好 1 次：`https://github.com/trending`（脚本抓不到）。
3. WebSearch 主题探针 **6 次固定**（每次只看摘要，不展开）：
   - `human review AI-generated code` ／ `context engineering AGENTS.md CLAUDE.md`
   - `agent governance enterprise audit` ／ `LLM wiki knowledge base agent memory`
   - `生成AI 導入事例 発表`（日本）／ `経済産業省 OR 個人情報保護委員会 OR IPA 生成AI ガイドライン`（日本）
4. 读 `candidates.json`，在 collected.md 和搜索摘要里 **grep 候选对象的名字**；不要逐个对象单独搜索（seed 的单独检索每周一次，周一做）。

## 2. 选题
- 从上述材料里按设计文档第 4 节打分，选出 **最多 12 条候选**（合计 ≥5），再过 3.2 排除项和 3.3 政策门槛，去掉与 seen.json 重复的。
- **只对这 ≤12 条候选 WebFetch 一次信息源**，确认正文和日期（48h 内，以一次信息源日期为准，无例外）。打不开或超期的直接去掉，不找替代。
- 最终 3–6 条，最多 8 条。不够就不凑：改为对候选池中一个关注对象做深读，并在报头说明当日无重大动态。
- **不要启动子代理**做分视角研究；需要并行时最多 1 个子代理、且只负责"验证候选 URL"。

## 3. 输出
生成**一个完整的 HTML 文件** `outputs/ai-briefing-YYYY-MM-DD.html`（日期用 bash `date` 确认，JST）。Light mode，CSS 内联，字号偏大。**沿用上一期（2026-10-06 号）的样式和结构**。
- 报头：日期 + 三视角说明。不要"本日のサマリー"。
- 每条：见出し 1 句／本文 200–300 字／视角标签（DEV / CONSULT / PM，可多选）＋每个视角一句「So what」／重要度（高＝今すぐ試せる・対応が要る，附「どう試す／どう対応する」一行；中＝追踪；低＝了解）／出典（一次信息源，可点击）／编辑评论 1 句。
- 高→中→低排序。末尾「短信」（≤3 行，可省略）和「候補プールの動き」（1–3 行）。
- 不要拆分文件；写完确认以 `</html>` 结尾。
- 更新 `index.html`（最上面加当天条目，href 为 `outputs/ai-briefing-YYYY-MM-DD.html`，核对文件存在）。
- 更新 `seen.json`（本次收录的事象）和 `candidates.json`（mentions / last_seen / sources / status；新名字加入）。

## 4. 发布与通知
- 按 `CLAUDE.md`：提交到工作分支并推送，再推送到 `main`（`state/` 目录也要一起提交），用 `git ls-tree -r --name-only origin/main | grep ai-briefing-$(date +%F)` 确认。
- 用 present_files 展示 HTML。
- Slack（Channel C0B967UK4AJ）发消息，**ハイライト每行只放消息本身，不加 [DEV] 之类前缀**：
  ```
  :robot_face: AI最新動向簡報 YYYY年M月D日号 を公開しました。

  本日のハイライト：
  - （见出し，每条一行，不分重要度）

  簡報リンク：
  <https://alphakt.github.io/news/outputs/ai-briefing-YYYY-MM-DD.html|YYYY年M月D日号>
  <https://alphakt.github.io/news/|News一覧>
  ```

## 5. 预算（超过即停止扩展范围）
WebFetch ≤ 15 次、WebSearch ≤ 8 次、子代理 ≤ 1 个。超出说明收集阶段跑偏了，回到第 2 步用已有材料定稿。
