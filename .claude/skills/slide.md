---
name: slide
description: Accenture 風 HTML スライド資料を `docs/templates/accenture_slide_template.html` をベースに自動生成する。引数でトピックを渡すと即生成、無しならヒアリング開始。
---

# /slide — アクセンチュア風スライド資料を作成

## このスキルの役割

`docs/templates/accenture_slide_template.html` を起点に、ユーザーが伝えたい内容を 5枚以内のスライド資料として `docs/<適切な名前>.html` に生成する。

## 実行手順

### Step 1: トピックの確定

引数（$ARGUMENTS）の扱い：
- **引数あり**: その内容をスライドの主題として採用。Step 2 に進む
- **引数なし**: ユーザーに「何の資料を作りますか？（プロジェクト概要 / 機能設計 / 進捗報告 など）」を AskUserQuestion で短く確認

### Step 2: 構成の素案を提示

主題から 3〜5枚のスライド構成案を提示し、ユーザーに確認する。テンプレートで使えるレイアウトパターンは：

- **[P1: Title]** タイトルスライド（必須・1枚目）
- **[P2: 3-col + Tech]** Problem / Solution / Outcome + 採用技術4カード
- **[P3: Sections A/B/C]** アーキテクチャ層 + データフロー + セットアップ手順
- **[P4: Pipeline + Stats]** プロセスフロー + ヒーロー数値
- **[P5: 2-col]** コマンドリファレンス + ロードマップ

短く（2-3センテンス）構成案を提示してユーザーに OK / 修正をもらう。

### Step 3: テンプレートをコピー

```bash
cp docs/templates/accenture_slide_template.html docs/<snake_case_name>.html
```

ファイル名はトピックから決定（例: `cicd_pipeline_overview.html`, `q1_progress_report.html`）。

### Step 4: コンテンツを差し替え

新ファイルを編集してテンプレートのプレースホルダー的内容を新トピックの内容に差し替える。**以下を絶対に守る**：

- `<title>` を更新
- Slide 1 のタイトル・サブタイトル・バッジ・URL を新内容に
- Slide 2-5 は構成案で選んだパターンに合わせて内容を埋める
- 不要なスライドは `<div class="slide">...</div>` ごと削除し、`slide-num` の `N / M` と JS の `total` 算出は自動なので何もしない
- ヘッドラインは `.headline` クラス（先頭の ">" は CSS で自動付与、本文には書かない）

### Step 5: デザイン原則の自動適用（[[reference-accenture-slide-template]] 参照）

CSS は触らない。色・フォント・余白方針はテンプレートに焼き込み済み：
- カラー: `--blue: #A100FF`（Accenture Purple）, `--gold: #FF50A0`（Pink）, `--dark: #000`
- フォント: sans-serif のみ（Georgia 禁止）
- フォントサイズ4階層: 10/13/17/30+
- 余白は装飾図形で埋めない（[[feedback-whitespace-in-slides]] 参照）

### Step 6: 完了報告

「`docs/<filename>.html` に作成しました。ブラウザで開いて確認してください。」と短く報告。コミット/プッシュはユーザーが明示的に依頼するまでしない。

## 引数

- `$ARGUMENTS`: 資料のトピック（省略可）

## 使用例

```
/slide CI/CD パイプラインの新メンバー向け解説
/slide 2026 Q1 進捗報告
/slide                        # 引数なし → ヒアリング開始
```
