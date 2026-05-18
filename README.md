# Anime Buzz Watcher

Anime Buzz Watcher は、アニメ関連コンテンツの話題度を集めて Discord Webhook に通知する課題用 Python アプリです。

AniList GraphQL API、Google News RSS、Reddit RSS を使って情報を取得し、話題度スコアで並べた上位 5 件を Discord Embed 形式で投稿します。X/Twitter API は任意です。`X_BEARER_TOKEN` が `.env` にある場合だけ、公式 X API で最近の投稿を検索して反応量をスコアに加えます。

## 機能

- AniList GraphQL API から人気アニメ情報を取得
- AniList の `season`、`seasonYear`、`status`、`format`、`episodes` を使って今期・最近の作品を優先
- Google News RSS からアニメ関連ニュースを取得
- Reddit RSS から `r/anime` の人気投稿を取得
- 任意で X/Twitter API から投稿数、いいね数、リポスト数、返信数、引用数を取得
- 任意で OpenAI API を使い、収集した情報を日本語で要約
- 話題度スコア順に並べ替え
- 上位 5 件を Discord Webhook に Embed 形式で通知
- 投稿済み URL を `data/posted_items.json` に保存し、重複投稿を防止
- 各 collector が失敗しても、アプリ全体はできるだけ止まらない設計

## 今期・最近のアニメを優先する仕組み

この Bot は、単純な人気ランキングではなく「今期アニメ」「現在放送中」「最近の新作」「劇場版やアニメ化ニュース」っぽいものを優先します。

AniList では、現在年と現在シーズンに近い `TV`、`TV_SHORT`、`MOVIE` を中心に取得します。`status` が `RELEASING` の作品は加点し、現在年・前年の作品も残しやすくしています。一方で、古い `seasonYear` の作品や `episodes` が多い作品は減点または除外します。

ONE PIECE、ポケモン、ナルト、ドラゴンボール、名探偵コナンなどの長期定番作品は、初期設定では `config/excluded_keywords.json` によって除外しています。除外したくない作品がある場合は、このファイルから該当キーワードを削除してください。

長期作品の判定は `config/filter_rules.json` で調整できます。

```json
{
  "exclude_long_running": true,
  "max_episode_count": 100,
  "max_old_season_years": 2,
  "prefer_releasing": true,
  "prefer_current_season": true
}
```

## 使用した API / RSS

- AniList GraphQL API: 人気・トレンド中のアニメ情報を取得
- Google News RSS: キーワードに関連するニュース記事を取得
- Reddit RSS: `r/anime` の hot 投稿を取得
- X API v2 Recent Search: 任意。`X_BEARER_TOKEN` がある場合のみ反応量を取得
- Discord Webhook: 取得した結果を Discord に投稿
- OpenAI API: 任意。`OPENAI_API_KEY` がある場合のみ、AI要約と話題の理由を生成

Slack API は使用していません。

## OpenAI API によるAI要約

授業で配布された OpenAI API キーを `.env` に設定すると、Discord投稿に「AI要約」「話題になっていそうな理由」「カテゴリ」「今期関連かどうか」が追加されます。

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5
```

`OPENAI_API_KEY` が未設定の場合、AI要約機能はスキップされ、今まで通り AniList、Google News RSS、Reddit RSS、Discord Webhook だけで動きます。API消費を避けたい場合は `--no-ai` を付けて実行してください。

```bash
python -m app.main --dry-run --no-ai
```

APIキーは必ず `.env` に入れてください。授業で配布されたAPIキーであっても、GitHubやREADME、スクリーンショットなどに公開しないでください。

## スコア計算

X/Twitter 反応スコア:

```text
reaction_score =
  投稿数 * 1
  + いいね数 * 0.1
  + リポスト数 * 0.5
  + 返信数 * 0.3
  + 引用数 * 0.4
```

全体の話題度スコア:

```text
trend_score =
  AniListの人気度
  + current_season_bonus
  + releasing_bonus
  + recent_year_bonus
  - old_title_penalty
  - long_running_penalty
  + Google Newsの記事数
  + Redditの反応数
  + Twitter/Xのreaction_score
```

X API がない場合は Twitter 反応スコアを使わず、AniList、Google News RSS、Reddit RSS で話題度を推定します。

## セットアップ手順

Python 3.11 以上を使用してください。

```bash
git clone <your-repository-url>
cd anime-buzz-watcher
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

`.env.example` をコピーして `.env` を作ります。

```bash
cp .env.example .env
```

Windows PowerShell の場合:

```powershell
Copy-Item .env.example .env
```

`.env` に Discord Webhook URL を設定します。

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token

# Optional. If this is empty, the app skips X/Twitter reactions and still works.
X_BEARER_TOKEN=

# Optional. If this is empty, the app skips AI summaries and still works.
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5

# Optional. Watch mode interval. 60 means once per hour.
CHECK_INTERVAL_MINUTES=60
```

## 実行方法

1回だけ実行する場合:

```bash
python -m app.main
```

実行すると、情報を取得して、未投稿の上位 5 件を Discord に投稿します。投稿済み URL は `data/posted_items.json` に保存されます。

Discord に投稿せずに動作確認したい場合は、dry-run を使います。

```bash
python -m app.main --dry-run
```

dry-run では、Discord Webhook には投稿せず、取得した上位 5 件をコンソールに表示します。`data/posted_items.json` も更新しません。

OpenAI APIキーが設定されている場合、dry-runでもAI要約が実行されます。APIを使わずに確認したい場合は、次のように `--no-ai` を付けます。

```bash
python -m app.main --dry-run --no-ai
```

1時間ごとに定期実行する場合:

```bash
python -m app.main --watch
```

定期実行モードでは、起動時に現在の通知間隔を表示し、各チェックごとに開始時刻、取得件数、重複スキップ件数、投稿件数、次回チェック予定時刻を表示します。停止するときはターミナルで `Ctrl+C` を押します。

定期実行でもDiscordに投稿せず確認したい場合:

```bash
python -m app.main --watch --dry-run
```

通知間隔は `.env` の `CHECK_INTERVAL_MINUTES` で変更できます。未設定の場合は60分です。不正な値の場合も60分に戻して警告ログを表示します。

```env
CHECK_INTERVAL_MINUTES=60
```

たとえば3時間ごとにしたい場合は、次のように設定します。

```env
CHECK_INTERVAL_MINUTES=180
```

## キーワードの変更

`config/trend_keywords.json` を編集すると、集めたいアニメ関連キーワードを変更できます。

```json
{
  "keywords": [
    "鬼滅の刃",
    "呪術廻戦",
    "薬屋のひとりごと",
    "葬送のフリーレン",
    "ガンダム",
    "アニメ化",
    "劇場版アニメ"
  ]
}
```


`data/posted_items.json` はアプリの重複投稿防止に必要なファイルなので、GitHub に含めてかまいません。ただし、自分が実行した後の投稿済み URL が入ったままだと提出先の環境で通知がスキップされる可能性があります。提出前は空の状態に戻すのがおすすめです。


## ディレクトリ構成

```text
anime-buzz-watcher/
  app/
    main.py
    config.py
    discord_webhook.py
    scoring.py
    storage.py
    collectors/
      anilist.py
      news.py
      reddit.py
      twitter_reactions.py
      trends.py
  config/
    trend_keywords.json
  data/
    posted_items.json
  .env.example
  requirements.txt
  README.md
  .gitignore
```
