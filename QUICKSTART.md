# クイックスタートガイド

> **対象**: 新規参画者、引継ぎ担当者  
> **目的**: 最短でシステムを理解し、起動・操作できるようにする

---

## 5分でスタート

### 前提条件

- Ubuntu 20.04以上のサーバー
- Docker & Docker Compose V2インストール済み
- VPN接続済み（IP: 54.248.141.21）

### ステップ1: プロジェクトディレクトリへ移動

```bash
cd /home/ubuntu/AWA-Webapp
```

### ステップ2: コンテナ起動

```bash
# 起動
docker compose up -d

# ログ確認
docker compose logs -f
```

### ステップ3: 動作確認

```bash
# API確認
curl http://localhost:8000/api/sites/

# ブラウザで確認
# http://54.248.141.21
```

---

## 主要コマンド

### コンテナ操作

```bash
# 起動
docker compose up -d

# 停止
docker compose down

# 再起動
docker compose restart

# ログ確認
docker compose logs -f backend

# コンテナ内に入る
docker compose exec backend bash
```

### デプロイ

```bash
# 最新コードを取得してデプロイ
docker compose down && \
git pull && \
docker compose up -d --build

# マイグレーション実行
docker compose exec backend python app/manage.py migrate
```

### バックアップ

```bash
# データベースバックアップ
docker compose exec db pg_dump -U postgres awa_webapp > \
  backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## トラブルシューティング

### コンテナが起動しない

```bash
# ログ確認
docker compose logs

# 完全リセット
docker compose down -v
docker compose up -d --build
```

### データベース接続エラー

```bash
# DBコンテナ確認
docker compose ps db

# DB再起動
docker compose restart db
```

### 403エラー（アクセス拒否）

- VPN接続を確認
- IPアドレスが許可リストにあるか確認: `nginx/nginx.conf`

---

## 詳細ドキュメント

- **[HANDOVER.md](./HANDOVER.md)**: 包括的な引継ぎドキュメント
- **[DEPLOYMENT.md](./DEPLOYMENT.md)**: デプロイ・運用マニュアル
- **[SECURITY.md](./SECURITY.md)**: セキュリティガイドライン
- **[rules.md](./rules.md)**: 開発ルール

---

## 主要な3つの画面

### 1. スタート画面（サイト選択）

- URL: `http://54.248.141.21/`
- 機能: クライアントサイトの選択・作成

### 2. 設定画面（変換ルール管理）

- 機能: 変換設定と変換ルールの管理
- 見出し、段落、表などのHTMLタグを設定

### 3. 変換実行画面

- 機能: Wordファイルのアップロード・HTML変換
- 変換結果のプレビューとダウンロード

---

## 重要なファイル・ディレクトリ

```
AWA-Webapp/
├── backend/app/settings.py      # Django設定
├── nginx/nginx.conf             # IP制限・ルーティング
├── docker-compose.yml           # コンテナ構成
├── .env                         # 環境変数（作成必要）
└── rules.md                     # 開発ルール
```

---

## よく使うAPI

```bash
# サイト一覧
curl http://localhost:8000/api/sites/

# Word変換
curl -X POST http://localhost:8000/api/convert/ \
  -F "file=@test.docx" \
  -F "setting_id=1"

# HTML取得
curl http://localhost:8000/api/download/?id=1
```

---

## Next Steps

1. **[HANDOVER.md](./HANDOVER.md)** を読む（60分）
2. 実際にWord変換を試す（15分）
3. 設定画面で変換ルールを編集してみる（30分）
4. デプロイ手順を確認する（30分）

---

**困ったときは**: HANDOVER.mdの「トラブルシューティング」セクションを参照

**最終更新日**: 2025年12月17日

