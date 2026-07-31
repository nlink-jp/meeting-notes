# RFP: meeting-notes

> Generated: 2026-07-31
> Status: Approved

## 1. Problem Statement

会議の文字起こし（TXT/VTT/SRT）を再利用可能な構造化データ——発言の逐語録・
理由付きの決定事項・要約の3層——にし、人間可読な議事録（Markdown/HTML）を
生成する。対象利用者は nlink-jp の運営者本人。

前身の meeting-note CLI（lab-series, Python + Vertex AI Gemini）は同じ問題を
解いていたが、**構造化データの生成が高頻度で失敗していた**。原因は設計に
内在する: 逐語録層を含む JSON 全体を単一の LLM 呼び出しで生成するため、
出力長が入力長に比例し、Gemini は長大な JSON 出力で高確率で破損する
（finish_reason=STOP のままの途中破損を含む。gem-transcribe ADR-0001 で
既知）。jsonfix による修復も構文しか直せず、意味を壊すことがある。

Claude Code Skill 化により、「分割抽出 → 断片ごとの検証 → 壊れた断片のみ
再試行 → 原本との引用突き合わせ」というエージェンティックなループで
根本原因（単発生成の脆さ）に対処する。

## 2. Functional Specification

### Commands / API Surface

- `/meeting-notes <transcript-file> [--lang ja|en] [--html]`
- 同梱スクリプト（スキルのワークフローが呼び出す。単体でも利用可能）:
  - `scripts/validate.py <json> [--part meta|item|synthesis] [--transcript <file>] [--strict]`
  - `scripts/assemble.py --meta ... --synthesis ... --items ... --transcript ... -o <json> --model <id>`
  - `scripts/compile.py <json> [-f markdown|html] [-o out] [--lang ja|en] [--tz <tz>]`

### Input / Output

- 入力: 文字起こしファイル（.txt / .vtt / .srt / エクスポート JSON）
- 出力: `<name>.json`（MeetingNote レコード、`schema.json` 準拠）+
  `<name>.md` または `<name>.html`（自己完結）
- JSON フォーマットは meeting-note CLI v0.2.x と完全互換
  （旧レコードはそのまま validate / compile 可能）

### Configuration

なし。旧 CLI の設定（GCP project / location / model / GCS bucket / ADC）は
すべて不要になる。出力言語は自動判定（CJK → ja）+ `--lang` 上書き。

### External Dependencies

- Claude Code（スキルホスト）
- python3 3.9+（同梱スクリプト用、**標準ライブラリのみ**）

## 3. Design Decisions

- **多段パイプラインを SKILL.md に明文化**: outline → 議題ごと抽出 →
  会議レベル合成 → 決定的アセンブル → 検証 → コンパイル。
  「全体を一発で書かない」ことが本スキルの存在理由なので、SKILL.md に
  最適化禁止の注意書きを置く。
- **決定的な処理はスクリプトに残す**: 検証・アセンブル・レンダリングは
  LLM にやらせない。meeting_id 導出は旧 CLI と同一アルゴリズム
  （SHA-256(title:date)[:12]）で互換維持。
- **引用は原本から検証**: `utterances[].text` は transcript からの逐語コピー
  とし、validate.py が空白正規化した部分一致で突き合わせる（警告ベース）。
  LLM 引用の捏造・改変ドリフトへの防御（feedback_llm_citation_verification）。
- **スクリプトは stdlib-only**: pydantic / Jinja2 / jsonschema を落とし、
  インストール先を選ばない。HTML テンプレートは Python 文字列に移植。
- **compile は ja/en 両対応**（旧 CLI は日本語ラベル固定だった改善点）。
- **プロンプトインジェクション防御は SKILL.md 冒頭**に配置
  （feedback_prompt_injection_position）。transcript はデータであり指示では
  ないと明記し、異常は報告に含める。
- **音声はスコープ外**: Claude は音声を直接処理できない。録音は
  gem-transcribe 等で先に文字起こしする運用に委ねる（案内のみ）。
- 補完関係: gem-transcribe（音声→transcript）の下流。lite-rag と組み合わせ
  れば旧 Phase 2（検索）の代替になる点も旧 CLI から変わらない。

### 明示的スコープ外

- 音声入力（旧 `-a`）
- SQLite / embedding / 検索（旧 Phase 2 と同じくスコープ外）
- Gemini 等の外部 LLM API 呼び出し

## 4. Development Plan

### Phase 1: Core

SKILL.md（多段ワークフロー）+ schema.json + validate/assemble/compile
スクリプト + unittest スイート（旧 CLI 実出力をフィクスチャにした互換
ラウンドトリップを含む）。

### Phase 2: Features

実運用フィードバック待ち。候補: VTT 話者ラベルの正規化支援、
長時間会議（2h+）向けの outline 分割指針の強化。

### Phase 3: Release

v0.1.0 — GitHub リポジトリ公開、`make package` の zip を Release 資産化、
skills-series umbrella へ submodule 追加、org profile / nlink-web-site
カタログ更新、旧 meeting-note リポジトリのアーカイブ（README に後継への
誘導を追記してから）。

## 5. Required API Scopes / Permissions

None.（旧 CLI が要求していた Vertex AI / GCS の IAM も不要になる）

## 6. Series Placement

Series: skills-series
Reason: Claude Code Skill そのものであり、1リポジトリ1スキル構成
（ADR-004）に従う。lab-series の前身プロジェクトは役目を終えアーカイブ。

## 7. External Platform Constraints

- Claude Code Skills の制約: ディレクトリ名 = スラッシュコマンド名 =
  frontmatter name。配布 zip はスキルフォルダがルート（claude.ai が受理
  するレイアウト）。
- スクリプトの実行環境は保証されないため stdlib-only 必須。
- claude.ai サンドボックスでも動作するよう、ネットワークアクセスは
  一切行わない。

---

## Discussion Log

- 出発点: 「meeting-note がやっていることは現代なら Skills で実現可能では」
  という問題提起。コード 1260 行のうち本質はプロンプトとスキーマのみで、
  残りの大半（Gemini クライアント・設定解決・jsonfix・型強制バリデーター）
  は API の世話をするコードだと確認。
- 動機の具体化: VTT/音声からの構造化で失敗が多発。診断の結果、逐語録層を
  含む長大 JSON の単発生成という設計が原因で、「壊れて当然の領域」で
  動かしていたと結論。gem-transcribe ADR-0001 の教訓（per-item salvage、
  一括 validate 禁止）が未反映だったことも確認。
- 代替案: (A) CLI のまま多段パイプライン化 — 確実だがコード増。
  (B) Skills 化 — エージェンティックなループが分割・再試行・引用回収を
  素で行う。利用実態が対話的（手元の会議をその場で処理）であること、
  Gemini 3 移行対象から外れることから B を採択。
- 名称: meeting-note が GitHub 上に既存のため meeting-notes とする（利用者
  指定）。旧リポジトリはアーカイブ。音声対応は gem-transcribe 委譲案も
  検討したが v0.1.0 を薄く保つためスコープ外とした（利用者決定）。
