# セキュリティガイドライン

> **対象**: 開発者、セキュリティ担当者  
> **目的**: セキュリティベストプラクティスと脆弱性対策

---

## 目次

1. [セキュリティ概要](#セキュリティ概要)
2. [ネットワークセキュリティ](#ネットワークセキュリティ)
3. [アプリケーションセキュリティ](#アプリケーションセキュリティ)
4. [データセキュリティ](#データセキュリティ)
5. [脆弱性対策](#脆弱性対策)
6. [セキュリティ監査](#セキュリティ監査)
7. [インシデント対応](#インシデント対応)

---

## セキュリティ概要

### セキュリティポリシー

AWA-Webappは以下のセキュリティ原則に基づいて設計されています：

1. **Defense in Depth（多層防御）**: 複数のセキュリティレイヤーで保護
2. **Principle of Least Privilege（最小権限の原則）**: 必要最小限の権限のみ付与
3. **Fail Securely（安全な失敗）**: エラー時も安全な状態を維持
4. **Security by Design（設計時からのセキュリティ）**: 後付けではなく設計段階から考慮

### セキュリティレイヤー

```
┌─────────────────────────────────────────────┐
│ Layer 1: ネットワーク（IP制限、VPN）         │
├─────────────────────────────────────────────┤
│ Layer 2: リバースプロキシ（Nginx）           │
├─────────────────────────────────────────────┤
│ Layer 3: アプリケーション（Django）          │
├─────────────────────────────────────────────┤
│ Layer 4: データベース（PostgreSQL）          │
├─────────────────────────────────────────────┤
│ Layer 5: コンテナ（Docker）                  │
└─────────────────────────────────────────────┘
```

---

## ネットワークセキュリティ

### IP制限（Layer 1）

**現在の設定**:
```nginx
# nginx/nginx.conf
geo $allowed_ip {
    default 0;                    # デフォルト拒否
    54.248.141.21 1;             # VPN IPのみ許可
    172.16.0.0/12 1;             # Docker内部ネットワーク
    192.168.0.0/16 1;            # Docker内部ネットワーク（予備）
}

if ($allowed_ip = 0) {
    return 403 "Access denied from your IP address: $remote_addr";
}
```

**セキュリティ効果**:
- VPN経由以外の全アクセスをブロック
- DDoS攻撃の大部分を防御
- 不正アクセスを根本から遮断

**IP制限の追加方法**:
```bash
# 1. 新しいIPアドレスを確認
curl ifconfig.me

# 2. nginx.confを編集
vim nginx/nginx.conf

# 3. geo $allowed_ip に追加
geo $allowed_ip {
    default 0;
    54.248.141.21 1;
    NEW.IP.ADDRESS.HERE 1;  # ← 追加
}

# 4. Nginxを再起動
docker compose restart nginx

# 5. 動作確認
curl -I http://54.248.141.21/
```

### ファイアウォール設定（推奨）

```bash
# UFW（Uncomplicated Firewall）の有効化
sudo ufw enable

# SSH許可（重要: ロックアウトされないように）
sudo ufw allow 22/tcp

# HTTP/HTTPS許可
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# VPN IPからのアクセスのみ許可（高度な設定）
sudo ufw allow from 54.248.141.21 to any port 80
sudo ufw allow from 54.248.141.21 to any port 443

# 状態確認
sudo ufw status verbose
```

### VPN設定の推奨

**現状の課題**:
- 固定IPアドレスに依存
- IPアドレス変更時に手動設定が必要

**推奨ソリューション（将来的に）**:
1. **WireGuard VPN**: 軽量で高速なVPN
2. **OpenVPN**: 標準的なVPN
3. **Tailscale**: ゼロコンフィグVPN

---

## アプリケーションセキュリティ

### Django セキュリティ設定

#### HTTPS強制（本番環境）

```python
# backend/app/settings.py

# HTTPS関連設定
SECURE_SSL_REDIRECT = True  # HTTPをHTTPSにリダイレクト
SECURE_HSTS_SECONDS = 31536000  # HSTS（HTTP Strict Transport Security）
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# クッキーのセキュリティ
SESSION_COOKIE_SECURE = True  # HTTPS経由のみでクッキー送信
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True  # JavaScriptからアクセス不可
CSRF_COOKIE_HTTPONLY = True

# X-Frame-Options（クリックジャッキング対策）
X_FRAME_OPTIONS = 'DENY'

# セキュアなコンテンツタイプ検出
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS対策
SECURE_BROWSER_XSS_FILTER = True
```

#### CORS設定の厳格化

**現在の設定（緩い）**:
```python
CORS_ALLOW_ALL_ORIGINS = True  # すべてのオリジンを許可
CORS_ALLOW_CREDENTIALS = True
```

**推奨設定（厳格）**:
```python
# 特定のオリジンのみ許可
CORS_ALLOWED_ORIGINS = [
    "http://54.248.141.21",
    "https://your-domain.com",
]

# メソッドの制限
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

# ヘッダーの制限
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_CREDENTIALS = True
```

#### REST API権限の強化

**現在の設定（緩い）**:
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # 認証不要
    ],
}
```

**推奨設定（厳格）**:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # 認証必須
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # レート制限（DDoS対策）
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # 匿名ユーザー: 1時間に100リクエスト
        'user': '1000/hour',  # 認証済みユーザー: 1時間に1000リクエスト
    },
}
```

#### ALLOWED_HOSTSの厳格化

**現在の設定（緩い）**:
```python
ALLOWED_HOSTS = ['*']  # すべてのホストを許可
```

**推奨設定（厳格）**:
```python
ALLOWED_HOSTS = [
    '54.248.141.21',
    'your-domain.com',
    'www.your-domain.com',
    'localhost',  # 開発環境のみ
]
```

### 認証・認可の実装（推奨）

#### トークン認証の実装

```python
# backend/api/views.py
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
        })
```

```python
# backend/api/urls.py
from django.urls import path
from .views import CustomAuthToken

urlpatterns = [
    path('auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
    # ...
]
```

#### パーミッションクラスの実装

```python
# backend/api/permissions.py
from rest_framework import permissions

class IsTenantMember(permissions.BasePermission):
    """テナントメンバーのみアクセス可能"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # オブジェクトがテナントに紐付いている場合
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.tenant
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """オブジェクトの所有者のみ編集可能"""
    
    def has_object_permission(self, request, view, obj):
        # 読み取りは誰でもOK
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 書き込みは所有者のみ
        return obj.user == request.user
```

---

## データセキュリティ

### 機密情報の管理

#### 環境変数の使用

```python
# backend/app/settings.py
from decouple import config

# Good: 環境変数から取得
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
POSTGRES_PASSWORD = config('POSTGRES_PASSWORD')

# Bad: ハードコード
# SECRET_KEY = 'django-insecure-hardcoded-key'
# POSTGRES_PASSWORD = 'postgres123'
```

#### .envファイルのセキュリティ

```bash
# .envファイルの権限を制限
chmod 600 .env

# Gitから除外
echo ".env" >> .gitignore
```

```.env
# .env.example（Gitにコミット可）
SECRET_KEY=your-secret-key-here
DEBUG=False
POSTGRES_DB=awa_webapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
```

### データベースセキュリティ

#### パスワードポリシーの強化

```python
# backend/app/settings.py

# パスワードバリデーション
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # 最小12文字
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# パスワードハッシュアルゴリズム（デフォルトで安全）
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # 推奨
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]
```

#### データベース接続の暗号化

```python
# PostgreSQL SSL接続（本番環境推奨）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require',  # SSL必須
        },
    }
}
```

### ログのセキュリティ

#### 機密情報のマスキング

```python
# backend/app/settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

**ログから除外すべき情報**:
- パスワード
- APIキー、トークン
- クレジットカード番号
- 個人識別情報（PII）

---

## 脆弱性対策

### OWASP Top 10 対策

#### 1. インジェクション対策

**SQLインジェクション**:
```python
# Good: ORMを使用（自動エスケープ）
Site.objects.filter(name=user_input)

# Good: パラメータ化クエリ
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM api_site WHERE name = %s", [user_input])

# Bad: 生SQLで文字列連結
cursor.execute(f"SELECT * FROM api_site WHERE name = '{user_input}'")
```

**コマンドインジェクション**:
```python
# Good: subprocessでリスト形式
import subprocess
subprocess.run(['ls', '-la', user_directory], check=True)

# Bad: シェル実行
subprocess.run(f'ls -la {user_directory}', shell=True)
```

#### 2. クロスサイトスクリプティング（XSS）対策

**Djangoテンプレート（自動エスケープ）**:
```django
{# Good: 自動エスケープ #}
{{ user_input }}

{# Bad: エスケープ無効化 #}
{{ user_input|safe }}
```

**React（自動エスケープ）**:
```typescript
// Good: 自動エスケープ
<div>{userInput}</div>

// Bad: dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{__html: userInput}} />
```

**手動エスケープ（必要な場合）**:
```python
from django.utils.html import escape
safe_html = escape(user_input)
```

#### 3. CSRF（クロスサイトリクエストフォージェリ）対策

**Djangoの自動CSRF保護**:
```python
# settings.py
MIDDLEWARE = [
    # ...
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF保護
    # ...
]

# CSRFトークンの免除（API限定）
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # RESTful APIのみ使用
def api_view(request):
    pass
```

**Reactでの CSRF トークン送信**:
```typescript
// CSRFトークンの取得
const getCookie = (name: string) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift();
};

// POSTリクエスト時にトークン送信
fetch('/api/convert/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCookie('csrftoken') || '',
  },
  body: formData,
});
```

#### 4. ファイルアップロードのセキュリティ

**拡張子チェック**:
```python
# backend/api/views.py

ALLOWED_EXTENSIONS = ['.docx']

def validate_file_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"許可されていない拡張子です: {ext}")
```

**ファイルサイズ制限**:
```python
# settings.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
```

**ファイル名のサニタイズ**:
```python
from django.utils.text import slugify
import uuid

def safe_filename(original_filename):
    """安全なファイル名を生成"""
    name, ext = os.path.splitext(original_filename)
    safe_name = slugify(name) or 'unnamed'
    unique_id = uuid.uuid4().hex[:8]
    return f"{safe_name}_{unique_id}{ext}"
```

**MIMEタイプ検証**:
```python
import magic

def validate_mime_type(file):
    """ファイルの実際のMIMEタイプを検証"""
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)  # ファイルポインタを戻す
    
    allowed_mimes = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if mime not in allowed_mimes:
        raise ValueError(f"許可されていないファイル形式です: {mime}")
```

#### 5. パストラバーサル対策

```python
from pathlib import Path
from django.conf import settings

def safe_file_path(user_filename):
    """安全なファイルパスを生成"""
    # パスを正規化
    base_path = Path(settings.MEDIA_ROOT).resolve()
    file_path = (base_path / user_filename).resolve()
    
    # ベースディレクトリ外へのアクセスを防止
    if not str(file_path).startswith(str(base_path)):
        raise ValueError("不正なファイルパスです")
    
    return file_path
```

### 依存パッケージの脆弱性チェック

```bash
# Pythonパッケージの脆弱性スキャン
pip install safety
safety check --file requirements.txt

# または、pipenvを使用
pip install pipenv
pipenv check

# npm パッケージの脆弱性スキャン（フロントエンド）
cd frontend
npm audit
npm audit fix  # 自動修正
```

---

## セキュリティ監査

### 定期監査チェックリスト

**月次チェック**:
- [ ] パッケージの脆弱性スキャン
- [ ] アクセスログのレビュー
- [ ] 異常なアクセスパターンの確認
- [ ] ディスク使用量の確認
- [ ] SSL証明書の有効期限確認

**四半期チェック**:
- [ ] セキュリティパッチの適用
- [ ] パスワードポリシーのレビュー
- [ ] IP制限リストのレビュー
- [ ] バックアップの復元テスト
- [ ] ログローテーション設定の確認

**年次チェック**:
- [ ] 包括的なセキュリティ監査
- [ ] ペネトレーションテスト（推奨）
- [ ] アクセス権限の全体レビュー
- [ ] インシデント対応計画の更新

### セキュリティスキャンツール

```bash
# Bandit: Pythonコードのセキュリティ脆弱性スキャン
pip install bandit
bandit -r backend/

# OWASP ZAP: Webアプリケーション脆弱性スキャン
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://54.248.141.21

# Trivy: Dockerイメージの脆弱性スキャン
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image awa-webapp_backend:latest
```

---

## インシデント対応

### インシデント対応プラン

#### フェーズ1: 検知

**検知方法**:
- ヘルスチェックの失敗
- 異常なログパターン
- ユーザーからの報告
- 監視アラート

**初動対応**:
```bash
# 1. 現在の状態確認
docker compose ps
docker compose logs --tail=100

# 2. アクセスログ確認
tail -n 100 nginx/logs/access.log

# 3. エラーログ確認
tail -n 100 nginx/logs/error.log
```

#### フェーズ2: 封じ込め

**不正アクセスの疑いがある場合**:
```bash
# 1. 該当IPからのアクセスをブロック
sudo ufw deny from <SUSPICIOUS_IP>

# 2. サービスを一時停止（緊急時）
docker compose down

# 3. データベースのバックアップ
docker compose exec db pg_dump -U postgres awa_webapp > incident_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### フェーズ3: 調査

```bash
# アクセスログから不審なアクセスを抽出
grep "404\|500" nginx/logs/access.log | tail -n 50

# 特定IPからのアクセスを確認
grep "<SUSPICIOUS_IP>" nginx/logs/access.log

# データベースログの確認
docker compose logs db | grep -i error
```

#### フェーズ4: 復旧

```bash
# 1. 最新の健全なバックアップから復元
docker compose exec -T db psql -U postgres awa_webapp < db_backup_YYYYMMDD.sql

# 2. サービス再起動
docker compose up -d

# 3. 動作確認
curl -f http://localhost:8000/api/sites/
```

#### フェーズ5: 事後対応

**レポート作成**:
- インシデント発生日時
- 影響範囲
- 原因分析
- 対応内容
- 再発防止策

**再発防止策の実施**:
- セキュリティ設定の見直し
- 監視の強化
- パッチの適用
- ドキュメントの更新

---

## まとめ

### セキュリティ優先度

**高優先度（即座に対応）**:
- IP制限の設定
- HTTPS化（SSL証明書）
- 環境変数の適切な管理
- 定期的なバックアップ

**中優先度（計画的に対応）**:
- CORS設定の厳格化
- 認証・認可の実装
- レート制限の実装
- セキュリティスキャンの自動化

**低優先度（将来的に対応）**:
- WAF（Webアプリケーションファイアウォール）
- SIEM（セキュリティ情報イベント管理）
- ペネトレーションテスト
- Bug Bountyプログラム

---

**最終更新日**: 2025年12月17日

