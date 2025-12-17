# デプロイ・運用マニュアル

> **対象**: システム運用担当者、DevOpsエンジニア  
> **目的**: デプロイ手順、運用タスク、バックアップ・復元の詳細手順

---

## 目次

1. [環境構築](#環境構築)
2. [デプロイ手順](#デプロイ手順)
3. [バックアップ・復元](#バックアップ復元)
4. [監視・メンテナンス](#監視メンテナンス)
5. [スケーリング](#スケーリング)
6. [SSL/HTTPS対応](#sslhttps対応)

---

## 環境構築

### 🔧 サーバー要件

| 項目 | 最小要件 | 推奨 |
|-----|---------|------|
| CPU | 2コア | 4コア |
| メモリ | 4GB | 8GB |
| ストレージ | 20GB | 50GB以上 |
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| Docker | 20.10+ | 最新版 |
| Docker Compose | V2 | V2最新版 |

### 初回セットアップ

#### 1. サーバーへのSSH接続

```bash
ssh ubuntu@54.248.141.21
```

#### 2. 必要なパッケージのインストール

```bash
# システムアップデート
sudo apt update && sudo apt upgrade -y

# Dockerのインストール
sudo apt install -y docker.io

# Docker Compose V2のインストール
sudo apt install -y docker-compose-plugin

# Dockerをsudoなしで実行できるようにする
sudo usermod -aG docker $USER

# 再ログイン（グループ権限を反映）
exit
ssh ubuntu@54.248.141.21
```

#### 3. リポジトリのクローン

```bash
cd /home/ubuntu
git clone <repository-url> AWA-Webapp
cd AWA-Webapp
```

#### 4. 環境変数の設定

```bash
# .envファイルの作成（本番環境用）
cat > .env << 'EOF'
# Django設定
SECRET_KEY=<strong-random-secret-key>
DEBUG=False
ALLOWED_HOSTS=54.248.141.21,your-domain.com

# データベース設定
POSTGRES_DB=awa_webapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-database-password>
DB_HOST=db
DB_PORT=5432
EOF

# 権限設定
chmod 600 .env
```

**SECRET_KEYの生成方法**:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 5. Dockerボリュームの作成

```bash
docker volume create awa-webapp_pgdata
```

#### 6. コンテナの起動

```bash
docker compose up -d --build
```

#### 7. データベースのマイグレーション

```bash
docker compose exec backend python app/manage.py migrate
```

#### 8. Django管理者ユーザーの作成

```bash
docker compose exec backend python app/manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: <strong-admin-password>
```

#### 9. 静的ファイルの収集

```bash
docker compose exec backend python app/manage.py collectstatic --noinput
```

#### 10. 動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/api/sites/

# フロントエンド確認
curl http://localhost/

# Nginx経由での確認
curl http://54.248.141.21/api/sites/
```

---

## デプロイ手順

### 通常デプロイ（コード更新時）

#### 手順1: 現在の状態確認

```bash
cd /home/ubuntu/AWA-Webapp

# 現在のブランチとコミットを確認
git status
git log -1

# 稼働中のコンテナを確認
docker compose ps
```

#### 手順2: バックアップの作成

```bash
# データベースバックアップ
docker compose exec backend python app/manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# または、PostgreSQLダンプ
docker compose exec db pg_dump -U postgres awa_webapp > db_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 手順3: 最新コードの取得

```bash
# 最新のコードをpull
git pull origin main

# 変更内容を確認
git log -5
git diff HEAD~1
```

#### 手順4: コンテナの停止

```bash
docker compose down
```

#### 手順5: イメージの再ビルド

```bash
# キャッシュを使わずにビルド
docker compose build --no-cache

# または、特定のサービスのみビルド
docker compose build --no-cache backend
```

#### 手順6: マイグレーションの実行

```bash
# マイグレーションが必要か確認
docker compose run --rm backend python app/manage.py showmigrations

# マイグレーション実行
docker compose run --rm backend python app/manage.py migrate
```

#### 手順7: コンテナの起動

```bash
docker compose up -d
```

#### 手順8: ログの確認

```bash
# すべてのサービスのログを確認（Ctrl+Cで終了）
docker compose logs -f

# バックエンドのみ確認
docker compose logs -f backend

# エラーがないか確認
docker compose logs backend | grep -i error
```

#### 手順9: ヘルスチェック

```bash
# APIの動作確認
curl -f http://localhost:8000/api/sites/ || echo "API check failed"

# フロントエンドの確認
curl -f http://localhost/ || echo "Frontend check failed"

# Nginx経由での確認
curl -f http://54.248.141.21/api/sites/ || echo "Nginx check failed"
```

#### 手順10: 動作テスト

```bash
# テストファイルで変換実行
docker compose exec backend bash
curl -X POST http://localhost:8000/api/convert/ \
  -F "file=@test_data/test.docx" \
  -F "setting_id=1"
exit
```

### ⚡ 緊急デプロイ（ホットフィックス）

重大なバグ修正時の最速デプロイ手順：

```bash
# 1行でデプロイ
cd /home/ubuntu/AWA-Webapp && \
git pull && \
docker compose down && \
docker compose up -d --build

# ログ確認
docker compose logs -f backend
```

### ロールバック手順

デプロイ後に問題が発生した場合：

```bash
# 前のコミットに戻す
git log  # コミットハッシュを確認
git reset --hard <previous-commit-hash>

# コンテナを再ビルド・起動
docker compose down
docker compose up -d --build

# データベースをバックアップから復元（必要に応じて）
docker compose exec -T backend python app/manage.py loaddata backup_YYYYMMDD_HHMMSS.json
```

---

## バックアップ・復元

### バックアップ戦略

#### 推奨バックアップスケジュール

| 対象 | 頻度 | 保存期間 | 方法 |
|-----|------|---------|------|
| データベース | 毎日 | 30日 | pg_dump |
| メディアファイル | 毎週 | 60日 | rsync |
| 設定ファイル | コード変更時 | 無期限 | Git |
| Dockerボリューム | 毎週 | 30日 | docker volume backup |

### データベースバックアップ

#### 方法1: Django dumpdata（推奨：開発環境）

```bash
# JSONフォーマットでエクスポート
docker compose exec backend python app/manage.py dumpdata \
  --indent=2 \
  --output=backup_$(date +%Y%m%d_%H%M%S).json

# 特定のアプリのみバックアップ
docker compose exec backend python app/manage.py dumpdata api \
  --output=api_backup_$(date +%Y%m%d_%H%M%S).json
```

#### 方法2: PostgreSQL pg_dump（推奨：本番環境）

```bash
# SQL形式でエクスポート
docker compose exec db pg_dump -U postgres awa_webapp > \
  db_backup_$(date +%Y%m%d_%H%M%S).sql

# 圧縮してエクスポート
docker compose exec db pg_dump -U postgres awa_webapp | \
  gzip > db_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# カスタムフォーマット（高速・圧縮）
docker compose exec db pg_dump -U postgres -Fc awa_webapp > \
  db_backup_$(date +%Y%m%d_%H%M%S).dump
```

#### 自動バックアップスクリプト

```bash
# backup.shを作成
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/ubuntu/AWA-Webapp"

# バックアップディレクトリ作成
mkdir -p $BACKUP_DIR/database
mkdir -p $BACKUP_DIR/media

# データベースバックアップ
cd $PROJECT_DIR
docker compose exec -T db pg_dump -U postgres awa_webapp | \
  gzip > $BACKUP_DIR/database/db_$DATE.sql.gz

# メディアファイルバックアップ
rsync -av --delete $PROJECT_DIR/backend/media/ $BACKUP_DIR/media/

# 古いバックアップを削除（30日以上前）
find $BACKUP_DIR/database -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

# 実行権限を付与
chmod +x /home/ubuntu/backup.sh

# Cronで自動実行（毎日午前3時）
crontab -e
# 以下を追加
0 3 * * * /home/ubuntu/backup.sh >> /home/ubuntu/backup.log 2>&1
```

### データベース復元

#### 方法1: Django loaddata

```bash
# JSONファイルから復元
docker compose exec backend python app/manage.py loaddata backup_20251217_120000.json
```

#### 方法2: PostgreSQL復元

```bash
# SQL形式から復元
docker compose exec -T db psql -U postgres awa_webapp < db_backup_20251217_120000.sql

# 圧縮ファイルから復元
gunzip -c db_backup_20251217_120000.sql.gz | \
  docker compose exec -T db psql -U postgres awa_webapp

# カスタムフォーマットから復元
docker compose exec -T db pg_restore -U postgres -d awa_webapp < db_backup_20251217_120000.dump
```

#### データベース完全リセット＆復元

```bash
# 1. 現在のデータベースを削除
docker compose exec db psql -U postgres -c "DROP DATABASE awa_webapp;"

# 2. データベースを再作成
docker compose exec db psql -U postgres -c "CREATE DATABASE awa_webapp;"

# 3. バックアップから復元
gunzip -c db_backup_20251217_120000.sql.gz | \
  docker compose exec -T db psql -U postgres awa_webapp

# 4. マイグレーション状態を確認
docker compose exec backend python app/manage.py showmigrations
```

### メディアファイルバックアップ

```bash
# ローカルにバックアップ
rsync -av /home/ubuntu/AWA-Webapp/backend/media/ /home/ubuntu/backups/media/

# S3にバックアップ（AWS CLIインストール済みの場合）
aws s3 sync /home/ubuntu/AWA-Webapp/backend/media/ s3://your-bucket/backups/media/

# 外部サーバーにバックアップ
rsync -av -e ssh /home/ubuntu/AWA-Webapp/backend/media/ user@backup-server:/backups/media/
```

### Dockerボリュームバックアップ

```bash
# ボリュームをtarアーカイブとしてバックアップ
docker run --rm \
  -v awa-webapp_pgdata:/data \
  -v /home/ubuntu/backups:/backup \
  ubuntu tar czf /backup/pgdata_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# ボリュームを復元
docker run --rm \
  -v awa-webapp_pgdata:/data \
  -v /home/ubuntu/backups:/backup \
  ubuntu tar xzf /backup/pgdata_20251217_120000.tar.gz -C /data
```

---

## 監視・メンテナンス

### システムモニタリング

#### リソース使用状況の確認

```bash
# CPUとメモリ使用状況
docker stats

# ディスク使用状況
df -h

# Docker関連のディスク使用量
docker system df

# コンテナごとのリソース確認
docker compose top
```

#### ログモニタリング

```bash
# リアルタイムログ監視
docker compose logs -f

# 最新100行のログ
docker compose logs --tail=100

# エラーログのみ表示
docker compose logs | grep -i error

# 特定の時間範囲のログ
docker compose logs --since="2025-12-17T10:00:00" --until="2025-12-17T12:00:00"
```

#### ヘルスチェックスクリプト

```bash
# healthcheck.shを作成
cat > /home/ubuntu/healthcheck.sh << 'EOF'
#!/bin/bash

# API ヘルスチェック
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sites/)
if [ "$API_STATUS" != "200" ]; then
    echo "[ERROR] API is down. Status: $API_STATUS"
    # Slackやメール通知を追加可能
else
    echo "[OK] API is healthy"
fi

# ディスク容量チェック
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "[WARNING] Disk usage is high: ${DISK_USAGE}%"
fi

# コンテナ状態チェック
UNHEALTHY=$(docker compose ps | grep -v "Up" | wc -l)
if [ "$UNHEALTHY" -gt 1 ]; then
    echo "[ERROR] Some containers are not running"
    docker compose ps
fi
EOF

chmod +x /home/ubuntu/healthcheck.sh

# Cronで5分ごとに実行
crontab -e
# 以下を追加
*/5 * * * * /home/ubuntu/healthcheck.sh >> /home/ubuntu/healthcheck.log 2>&1
```

### 定期メンテナンス

#### ログローテーション

```bash
# Nginxログのローテーション
cat > /etc/logrotate.d/nginx-docker << 'EOF'
/home/ubuntu/AWA-Webapp/nginx/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        docker compose exec nginx nginx -s reopen
    endscript
}
EOF
```

#### xml_dataディレクトリのクリーンアップ

```bash
# cleanup.shを作成
cat > /home/ubuntu/cleanup.sh << 'EOF'
#!/bin/bash

XML_DIR="/home/ubuntu/AWA-Webapp/backend/xml_data"

# 7日以上前のXMLディレクトリを削除
find $XML_DIR -type d -mtime +7 -exec rm -rf {} +

echo "Cleanup completed: $(date)"
EOF

chmod +x /home/ubuntu/cleanup.sh

# Cronで毎日午前2時に実行
crontab -e
# 以下を追加
0 2 * * * /home/ubuntu/cleanup.sh >> /home/ubuntu/cleanup.log 2>&1
```

#### Dockerシステムクリーンアップ

```bash
# 未使用のイメージ、コンテナ、ボリュームを削除
docker system prune -af --volumes

# 定期的にCronで実行（毎週日曜日午前4時）
crontab -e
# 以下を追加
0 4 * * 0 docker system prune -af >> /home/ubuntu/docker_prune.log 2>&1
```

---

## スケーリング

### 垂直スケーリング（リソース増強）

#### docker-compose.ymlでリソース制限

```yaml
# docker-compose.yml
services:
  backend:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

#### PostgreSQLのパフォーマンスチューニング

```yaml
services:
  db:
    # ...
    environment:
      # 共有バッファ（メモリの25%程度）
      - POSTGRES_SHARED_BUFFERS=2GB
      # ワークメモリ
      - POSTGRES_WORK_MEM=50MB
      # メンテナンスワークメモリ
      - POSTGRES_MAINTENANCE_WORK_MEM=512MB
    command:
      - "postgres"
      - "-c"
      - "max_connections=200"
      - "-c"
      - "shared_buffers=2GB"
```

### 水平スケーリング（複数インスタンス）

#### ロードバランサー構成（将来的に）

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                ↓
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Backend 1│     │ Backend 2│     │ Backend 3│
    └──────────┘     └──────────┘     └──────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ↓
                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │   (Primary)     │
                  └─────────────────┘
```

#### Docker Swarmモード（推奨）

```bash
# Swarmモード初期化
docker swarm init

# スタックをデプロイ
docker stack deploy -c docker-compose.yml awa-webapp

# バックエンドをスケールアウト
docker service scale awa-webapp_backend=3

# サービス状態確認
docker service ls
docker service ps awa-webapp_backend
```

---

## SSL/HTTPS対応

### Let's Encrypt証明書の設定

#### 1. Certbotのインストール

```bash
sudo apt install -y certbot python3-certbot-nginx
```

#### 2. 証明書の取得

```bash
# ドメインの証明書を取得
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com
```

#### 3. Nginx設定の更新

```nginx
# nginx/nginx.conf
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # HTTPからHTTPSへリダイレクト
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL証明書
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # ... 既存の設定
}
```

#### 4. docker-compose.ymlの更新

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"  # HTTPS追加
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro  # 証明書マウント
```

#### 5. 証明書の自動更新

```bash
# Cronで毎月1日に更新
crontab -e
# 以下を追加
0 0 1 * * certbot renew --quiet && docker compose restart nginx
```

---

## まとめ

### 運用チェックリスト

**デイリータスク**:
- [ ] システムログの確認
- [ ] エラーログの確認
- [ ] ディスク使用量の確認
- [ ] コンテナ稼働状況の確認

**ウィークリータスク**:
- [ ] データベースバックアップの確認
- [ ] メディアファイルバックアップ
- [ ] xml_dataディレクトリのクリーンアップ
- [ ] Dockerシステムクリーンアップ

**マンスリータスク**:
- [ ] セキュリティアップデートの適用
- [ ] パフォーマンスレビュー
- [ ] バックアップの復元テスト
- [ ] SSL証明書の有効期限確認

---

**最終更新日**: 2025年12月17日

