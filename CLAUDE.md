# news — 日次AI簡報 リポジトリ運用ルール

alphakt 社内向け「AI最新動向簡報」を毎日生成・公開するリポジトリ。
**GitHub Pages は `main` ブランチのルートから配信される。** このため、生成物が
`main` に届かない限りページは 404 になる（過去に発生済み）。以下は必須手順。

## ⚠️ 最重要：公開は必ず `main` に届けること

GitHub Pages = `main` ブランチ配信。作業ブランチ（`claude/...`）に書いて停止すると、
**Pages には一切反映されず毎日404になる**。これがこのパイプライン最大の落とし穴。

毎回のランで、以下のどちらかで生成物を必ず `main` に乗せる:

- **推奨**: 作業ブランチにコミット → push →（権限がある場合）`main` へ直接 push、
  または PR を作成して即マージ。
- 作業ブランチへの push だけで終えない。「`main` に存在するか」を必ず確認する:
  ```
  git ls-tree -r --name-only origin/main | grep ai-briefing-$(date +%F)
  ```
  上記が空なら未公開。`git push origin HEAD:main` 等で main に反映する。

公開確認 URL（反映まで数分かかる）:
- 当日: `https://alphakt.github.io/news/outputs/ai-briefing-YYYY-MM-DD.html`
- 一覧: `https://alphakt.github.io/news/`

## ファイル配置（規約を1つに統一）

- 簡報本体: **`outputs/ai-briefing-YYYY-MM-DD.html`** （日付はJST、`date` で確認）
  - `src/` や `briefings/` など他のフォルダは使わない（過去に3規約が混在し404の原因になった）。
- アーカイブ入口: ルートの `index.html`。新しい簡報は**一番上**に追記（新しい順）。
  - エントリの `href` は必ず `outputs/ai-briefing-YYYY-MM-DD.html`（実在パスと一致させる）。
- 簡報内の「一覧へ戻る」リンクは `../index.html`（`outputs/` から見た相対）。

## 生成時の禁止事項 / 注意

- **ファイルを分割しない**。`split` で `frag_aa` 等の断片を作ってコミットすると本文が
  欠落する（2026-06-08で発生）。HTMLは1ファイルで完結させて書き込む。
- 書き込み後、`</html>` まで揃った完全なファイルであることを確認する。
- 出典は実在URLのみ。リンク先を確認できない情報・URLは載せない（捏造禁止）。
- index.html を更新したら、追加した `href` のファイルが実在するか必ず照合する。

## 内容要件（簡報そのもの）

**編集方針は `docs/briefing-design.md` が正。** 要点:
- 読者は DEV（開発者）/ CONSULT（コンサルタント、クライアントは日本企業）/ PM（プロジェクト管理者）の 3 視点。
  各記事に視点タグと視点ごとの「So what」を付ける。どの視点にも So what が書けない記事は載せない。
- 資金調達・評価額・株価は既定で除外（可用性・価格が変わる場合のみ例外）。
- 政策は「署名・成立済み／可用性・データ・責任・調達に影響／日・米・EU・中」をすべて満たすものだけ。
- 重要度は行動可能性で決める（高＝今すぐ試せる・対応が要る）。
- 件数は 3–6 件目安、最大 8。無理に埋めない。動きのない日は候補プールの 1 件を深読みする。
- すべて日本語。報頭に当日日付（`date` で確認）。本文 200–300 字、出典は一次情報の `<a href>`、コメント 1 文。
- 「本日のサマリー」は付けない。Light mode。

## 情報収集の仕組み

- `sources.json`: 固定源池。`feeds` は `scripts/collect.py` が自動取得、`pages` は WebFetch で確認、
  `unreachable` は取得不能な源とその理由。**源を追加するときは必ずこの環境で取得できることを確認してから登録する。**
- `python3 scripts/collect.py --hours 48 --out <scratchpad>/collected.md` で直近 48h の記事一覧を作る。
  `--health` で feed の疎通確認。
- `candidates.json`: 候補プール（製品・概念・手法）。昇格・退出の規則は設計文書第 4 節。固定 watchlist は持たない。
- `seen.json`: 収録済み事象。重複収録を防ぐ。毎回追記する。
- 実行環境は **Network access = Full** が必須。Trusted のままだと一次情報源がほぼ全て 403 になる
  （2026-10-02 に判明。routine の環境設定を確認すること）。
- 定時タスクの prompt は `docs/briefing-prompt.md`（routine 側の設定は仓库外なので、変更時は貼り直す）。

## 完了時

- 生成物が `main` にあることを確認（上記コマンド）。
- Pages リンクを present_files で提示し、Slack（Channel C0B967UK4AJ）へ通知。
