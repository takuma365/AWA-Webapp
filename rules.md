# AWA-Webapp 開発ルール

## デプロイ手順

### コード修正後のデプロイ

コードを修正した後は、必ず以下の手順でデプロイしてください：

```bash
# 1. 現在のサービスを停止
docker compose down

# 2. 最新のコードを取得
git pull origin main

# 3. イメージをリビルド
docker compose build --no-cache

# 4. マイグレーションを実行
docker compose run --rm backend python app/manage.py migrate

# 5. サービスを起動
docker compose up -d

# 6. ログを確認
docker compose logs -f
```

### 開発用簡単デプロイ

```bash
# 一発デプロイ
docker compose down && git pull && docker compose up -d --build

# ログ確認
docker compose logs -f backend
```

### 本番用詳細デプロイ

```bash
# 1. バックアップ作成
docker compose exec backend python app/manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# 2. デプロイ
docker compose down
git pull origin main
docker compose build --no-cache
docker compose run --rm backend python app/manage.py migrate
docker compose up -d

# 3. ヘルスチェック
curl -f http://localhost:8000/api/sites/ || echo "API check failed"
```

## 開発ルール

### 1. コード修正時の注意事項

- 修正後は必ず上記のデプロイ手順を実行する
- データベースの変更がある場合は必ずマイグレーションを実行する
- 本番環境での修正は慎重に行い、バックアップを取る

### 2. コミットルール

- コミットメッセージは日本語で分かりやすく記述する
- 機能追加・修正・バグ修正を明確に区別する
- 例：`feat: 句点分割機能を追加`、`fix: HTMLタグ分割問題を修正`

### 3. テストルール

- 新機能追加時は必ずテストを実行する
- APIの変更時はcurlコマンドで動作確認する
- フロントエンドの変更時はブラウザで動作確認する

### 4. トラブルシューティング

```bash
# コンテナ再起動のみ
docker compose restart

# 特定のサービスのみ再起動
docker compose restart backend
docker compose restart frontend

# ログ確認
docker compose logs -f backend
docker compose logs -f frontend
```

### 5. データベース操作

```bash
# バックアップ作成
docker compose exec backend python app/manage.py dumpdata > backup.json

# バックアップ復元
docker compose exec backend python app/manage.py loaddata backup.json

# マイグレーション確認
docker compose exec backend python app/manage.py showmigrations
```

## 環境設定

### 必要な環境変数

- `DATABASE_URL`: PostgreSQL接続情報
- `SECRET_KEY`: Django秘密鍵
- `DEBUG`: デバッグモード設定

### ファイル配置

- `.env`ファイルはGitに含めない
- `backend/.env.example`を参考に各自設定する
- 本番環境では適切な環境変数を設定する

## 🔧 中点除去フラグ機能

### 概要
フロントエンドで中点（・）の除去とliタグの使用をON/OFFできる機能を追加しました。

### 機能詳細

#### バックエンド変更
- **モデル**: `Site`モデルに`use_bullet_points`フィールドを追加
- **シリアライザー**: `SiteSerializer`に新しいフィールドを追加
- **変換処理**: `xml_to_html_converter.py`でフラグに基づいて処理を分岐

#### フラグの動作
- **ON（デフォルト）**: 中点（・）を除去してliタグでリスト表示
- **OFF**: 中点を保持してbrタグで改行表示

#### フロントエンド実装
クライアントサイトのドメイン設定の真上に以下のUIを追加：
- チェックボックス: 「中点を除去してliタグを使う」
- デフォルト値: ON（true）

### データベース変更
```sql
ALTER TABLE "api_site" ADD COLUMN "use_bullet_points" boolean DEFAULT true NOT NULL;
```

### 使用方法
1. フロントエンドでサイト設定画面を開く
2. クライアントドメイン設定の真上にあるチェックボックスを操作
3. 設定を保存
4. Wordファイルをアップロードして変換実行

## 緊急時対応

### サービスが起動しない場合

1. ログを確認：`docker compose logs -f`
2. コンテナを完全に削除：`docker compose down -v`
3. イメージを再ビルド：`docker compose build --no-cache`
4. サービスを起動：`docker compose up -d`

### データベースエラーの場合

1. バックアップを確認
2. マイグレーションを再実行
3. 必要に応じてデータベースをリセット

## 更新履歴

- 2025/01/XX: デプロイ手順を追加
- 2025/01/XX: 開発ルールを追加
- 2025/07/23: 中点除去フラグ機能を追加（use_bullet_points） 