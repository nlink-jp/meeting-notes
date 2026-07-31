# meeting-notes

会議の文字起こし（TXT / VTT / SRT）を、検証済みの3層構造 JSON レコード——
発言の逐語録・理由付きの決定事項・要約——に構造化し、Markdown または
自己完結 HTML の議事録にコンパイルする Claude Code Skill。
`/meeting-notes <transcript-file>` で呼び出す。

アーカイブ済みの [meeting-note](https://github.com/nlink-jp/meeting-note)
CLI の後継。CLI は JSON 全体を単一の LLM 呼び出しで生成しており、長い会議では
出力破損が頻発した（逐語録層があるため出力が入力と同程度に長くなる）。
本スキルは小さな断片ごとに抽出し、同梱スクリプトでその場で検証、壊れた断片
だけを再抽出し、すべての引用を元の文字起こしと突き合わせて検証する——
CLI の修復コードが近似していたことを、エージェンティックなループが素で行う。
JSON フォーマットは不変で、既存レコードはそのままコンパイルできる。

## インストール

リリース zip から（claude.ai → Settings → Skills にそのままアップロードも可）:

```bash
unzip meeting-notes-vX.Y.Z.zip -d ~/.claude/skills/
```

チェックアウトから:

```bash
make install
```

要件: Claude Code と `python3`（3.9+、標準ライブラリのみ。同梱の検証・
コンパイルスクリプトが使用）。

## 使い方

```
/meeting-notes path/to/transcript.vtt
/meeting-notes minutes.txt --lang en
/meeting-notes standup.srt --html
```

多段の抽出 → 検証 → 突き合わせワークフローを経て、入力の隣に生成する:

- `<name>.json` — 構造化 MeetingNote レコード
  （スキーマ: `meeting-notes/schema.json`、
  仕様: `meeting-notes/references/data-format.md`）
- `<name>.md` — 議事録（`--html` 指定時は自己完結の `<name>.html`）

音声入力はスコープ外——先に
[gem-transcribe](https://github.com/nlink-jp/gem-transcribe) 等で文字起こし
してから本スキルにかけること。

旧 CLI が生成したレコードは直接再コンパイルできる:

```bash
python3 ~/.claude/skills/meeting-notes/scripts/compile.py meeting.json -o meeting.md
python3 ~/.claude/skills/meeting-notes/scripts/compile.py meeting.json -f html -o meeting.html --lang en
```

## 開発

| コマンド | 用途 |
|---------|------|
| `make check`（= `make test`） | 構造検証 + スクリプトの動作テスト |
| `make install` | `~/.claude/skills/meeting-notes` へコピー |
| `make package` | `dist/meeting-notes-vX.Y.Z.zip` を作成（zip ルート = スキルフォルダ） |

## ドキュメント

- [データフォーマット仕様](meeting-notes/references/data-format.md)（英語）
- [RFP / 設計文書](docs/ja/meeting-notes-rfp.ja.md)
- [English README](README.md)

## ライセンス

MIT
