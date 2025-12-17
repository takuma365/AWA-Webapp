# マルチテナント化実装ガイド

> **対象**: 開発者、アーキテクト  
> **目的**: 他社向けSaaSサービスとしてマルチテナント化する具体的な実装手順

---

## 目次

1. [マルチテナント化の目的](#マルチテナント化の目的)
2. [アーキテクチャ選択](#アーキテクチャ選択)
3. [実装手順（ステップバイステップ）](#実装手順)
4. [マイグレーション戦略](#マイグレーション戦略)
5. [サブドメイン設定](#サブドメイン設定)
6. [課金・プラン管理](#課金プラン管理)
7. [テスト戦略](#テスト戦略)

---

## マルチテナント化の目的

### ビジネス目標

- **複数企業へのサービス提供**: 現在の単一企業向けから、複数企業向けSaaSへ
- **スケーラビリティ**: 新規顧客の追加が容易
- **データ分離**: 企業間でデータを完全に分離
- **柔軟な課金**: プランに応じた機能制限・課金

### ユースケース

```
企業A (company-a.awa-webapp.com)
├── ユーザー: user-a1@company-a.com
├── サイト: 3個
├── プラン: Basic
└── 月間変換: 50回

企業B (company-b.awa-webapp.com)
├── ユーザー: user-b1@company-b.com
├── サイト: 10個
├── プラン: Pro
└── 月間変換: 500回
```

---

## アーキテクチャ選択

### 3つのアプローチ比較

| 方式 | データ分離 | 実装難易度 | コスト | 推奨度 |
|-----|-----------|-----------|--------|--------|
| **テーブル共有** | tenant_id列 | 低 | 低 | ⭐⭐⭐⭐⭐ |
| **スキーマ分離** | PostgreSQLスキーマ | 中 | 中 | ⭐⭐⭐ |
| **データベース分離** | 別DB | 高 | 高 | ⭐⭐ |

### 推奨: テーブル共有方式

**理由**:
- Django との親和性が高い
- 既存コードの変更が最小限
- リソース効率が良い
- 小〜中規模SaaSに最適

**アーキテクチャ図**:
```
┌────────────────────────────────────────────┐
│            Application Layer               │
│  (Tenantを意識したクエリフィルタ)          │
└────────────────┬───────────────────────────┘
                 ↓
┌────────────────────────────────────────────┐
│          PostgreSQL Database               │
│  ┌──────────────────────────────────────┐ │
│  │        api_tenant テーブル           │ │
│  ├────┬─────────┬──────────┬──────────┤ │
│  │ id │ name    │subdomain │ plan     │ │
│  ├────┼─────────┼──────────┼──────────┤ │
│  │ 1  │企業A    │company-a │basic     │ │
│  │ 2  │企業B    │company-b │pro       │ │
│  └────┴─────────┴──────────┴──────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │        api_site テーブル             │ │
│  ├────┬──────────┬──────────┬────────┤ │
│  │ id │tenant_id │ name     │ url    │ │
│  ├────┼──────────┼──────────┼────────┤ │
│  │ 1  │    1     │サイトA1  │site-a1 │ │
│  │ 2  │    1     │サイトA2  │site-a2 │ │
│  │ 3  │    2     │サイトB1  │site-b1 │ │
│  └────┴──────────┴──────────┴────────┘ │
└────────────────────────────────────────────┘
```

---

## 実装手順

### Phase 1: モデル設計（所要時間: 2時間）

#### ステップ1.1: Tenantモデルの作成

```python
# backend/api/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """テナント（企業）モデル"""
    
    # 基本情報
    name = models.CharField(_('企業名'), max_length=255)
    subdomain = models.CharField(
        _('サブドメイン'), 
        max_length=50, 
        unique=True,
        help_text=_('例: company-a （company-a.awa-webapp.com）')
    )
    
    # プラン情報
    PLAN_CHOICES = [
        ('free', _('フリープラン')),
        ('basic', _('ベーシックプラン')),
        ('pro', _('プロプラン')),
        ('enterprise', _('エンタープライズプラン')),
    ]
    plan = models.CharField(
        _('プラン'), 
        max_length=20, 
        choices=PLAN_CHOICES, 
        default='free'
    )
    
    # 制限事項
    max_sites = models.IntegerField(_('最大サイト数'), default=3)
    max_conversions_per_month = models.IntegerField(_('月間変換上限'), default=50)
    max_file_size_mb = models.IntegerField(_('最大ファイルサイズ(MB)'), default=10)
    
    # ストレージ使用量
    storage_used_mb = models.FloatField(_('使用ストレージ(MB)'), default=0)
    max_storage_mb = models.IntegerField(_('ストレージ上限(MB)'), default=1000)
    
    # 課金情報（将来的に）
    stripe_customer_id = models.CharField(
        _('Stripe顧客ID'), 
        max_length=255, 
        blank=True
    )
    subscription_start_date = models.DateField(
        _('契約開始日'), 
        null=True, 
        blank=True
    )
    subscription_end_date = models.DateField(
        _('契約終了日'), 
        null=True, 
        blank=True
    )
    
    # ステータス
    is_active = models.BooleanField(_('有効'), default=True)
    is_trial = models.BooleanField(_('トライアル中'), default=True)
    trial_end_date = models.DateField(_('トライアル終了日'), null=True, blank=True)
    
    # タイムスタンプ
    created_at = models.DateTimeField(_('作成日時'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新日時'), auto_now=True)
    
    class Meta:
        verbose_name = _('テナント')
        verbose_name_plural = _('テナント')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.subdomain})"
    
    def is_within_limits(self, check_type='conversions'):
        """制限内かチェック"""
        if check_type == 'conversions':
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            conversions_count = ConversionOutput.objects.filter(
                setting__site__tenant=self,
                created_at__startswith=current_month
            ).count()
            return conversions_count < self.max_conversions_per_month
        
        elif check_type == 'sites':
            sites_count = self.sites.filter(active=True).count()
            return sites_count < self.max_sites
        
        elif check_type == 'storage':
            return self.storage_used_mb < self.max_storage_mb
        
        return True


class TenantUser(models.Model):
    """テナントとユーザーの紐付け"""
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE,
        related_name='tenant_users'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    
    ROLE_CHOICES = [
        ('owner', _('オーナー')),
        ('admin', _('管理者')),
        ('member', _('メンバー')),
    ]
    role = models.CharField(
        _('役割'), 
        max_length=20, 
        choices=ROLE_CHOICES,
        default='member'
    )
    
    is_active = models.BooleanField(_('有効'), default=True)
    joined_at = models.DateTimeField(_('参加日時'), auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant', 'user']
        verbose_name = _('テナントユーザー')
        verbose_name_plural = _('テナントユーザー')
    
    def __str__(self):
        return f"{self.user.username} @ {self.tenant.name} ({self.role})"
```

#### ステップ1.2: 既存モデルの修正

```python
# backend/api/models.py

class Site(models.Model):
    """サイト設定モデル"""
    
    # 追加: テナント紐付け
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='sites',
        verbose_name=_('テナント')
    )
    
    name = models.CharField(_('サイト名'), max_length=255)
    url = models.CharField(
        _('URL'), 
        max_length=100, 
        help_text=_('サイトのURL（英小文字）')
    )
    # ... その他のフィールドは変更なし
    
    class Meta:
        verbose_name = _('サイト')
        verbose_name_plural = _('サイト')
        ordering = ['name']
        # 変更: テナント内でURLが一意
        unique_together = [['tenant', 'url']]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


# ConversionSetting, ConversionRuleは間接的にテナントと紐付く（Siteを通じて）
# そのため、直接tenant_idを追加する必要はない
```

### Phase 2: Middleware実装（所要時間: 1時間）

#### ステップ2.1: TenantMiddlewareの作成

```python
# backend/api/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .models import Tenant, TenantUser


class TenantMiddleware(MiddlewareMixin):
    """
    リクエストからテナントを識別し、request.tenantに設定するミドルウェア
    
    識別方法:
    1. サブドメインから（例: company-a.awa-webapp.com）
    2. HTTPヘッダーから（例: X-Tenant-Subdomain: company-a）
    3. URLパラメータから（例: ?tenant=company-a）
    """
    
    def process_request(self, request):
        tenant = self._get_tenant_from_request(request)
        
        if tenant:
            # テナントが有効かチェック
            if not tenant.is_active:
                return JsonResponse(
                    {'error': 'このテナントは無効化されています。'},
                    status=403
                )
            
            # トライアル期間チェック
            if tenant.is_trial and tenant.trial_end_date:
                from datetime import date
                if date.today() > tenant.trial_end_date:
                    return JsonResponse(
                        {'error': 'トライアル期間が終了しました。プランをアップグレードしてください。'},
                        status=402  # Payment Required
                    )
            
            request.tenant = tenant
        else:
            # テナント不明の場合はNone（デフォルトテナントを使う等の処理も可能）
            request.tenant = None
        
        return None
    
    def _get_tenant_from_request(self, request):
        """リクエストからテナントを特定"""
        
        # 方法1: サブドメインから
        host = request.get_host()
        parts = host.split('.')
        if len(parts) >= 3:  # subdomain.domain.com
            subdomain = parts[0]
            try:
                return Tenant.objects.get(subdomain=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        # 方法2: HTTPヘッダーから（開発・テスト用）
        subdomain_header = request.META.get('HTTP_X_TENANT_SUBDOMAIN')
        if subdomain_header:
            try:
                return Tenant.objects.get(subdomain=subdomain_header, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        # 方法3: URLパラメータから（開発・テスト用）
        subdomain_param = request.GET.get('tenant')
        if subdomain_param:
            try:
                return Tenant.objects.get(subdomain=subdomain_param, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        # 方法4: 認証ユーザーから（フォールバック）
        if request.user and request.user.is_authenticated:
            membership = TenantUser.objects.filter(
                user=request.user, 
                is_active=True
            ).first()
            if membership:
                return membership.tenant
        
        return None
```

#### ステップ2.2: settings.pyに追加

```python
# backend/app/settings.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'api.middleware.TenantMiddleware',  # ✨ 追加（認証後に配置）
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Phase 3: ViewSetの修正（所要時間: 2時間）

#### ステップ3.1: テナントフィルタリングの実装

```python
# backend/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class TenantFilteredViewSetMixin:
    """テナントでフィルタリングするMixin"""
    
    def get_queryset(self):
        """ログインユーザーのテナントに紐付くデータのみ取得"""
        queryset = super().get_queryset()
        
        # request.tenantがない場合は空のクエリセットを返す
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        
        # tenant フィールドがある場合
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=self.request.tenant)
        
        # site を通じてテナントに紐付く場合（ConversionSettingなど）
        if hasattr(queryset.model, 'site'):
            return queryset.filter(site__tenant=self.request.tenant)
        
        return queryset
    
    def perform_create(self, serializer):
        """新規作成時に自動的にテナントを設定"""
        if hasattr(serializer.Meta.model, 'tenant'):
            serializer.save(tenant=self.request.tenant)
        else:
            serializer.save()


class SiteViewSet(TenantFilteredViewSetMixin, viewsets.ModelViewSet):
    """サイト情報のCRUD操作用ViewSet"""
    serializer_class = SiteSerializer
    
    def get_queryset(self):
        """テナント + activeフィルタ"""
        queryset = Site.objects.filter(active=True)
        
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        
        return queryset.filter(tenant=self.request.tenant)
    
    def perform_create(self, serializer):
        """新規作成時にテナントを自動設定"""
        tenant = self.request.tenant
        
        # サイト数制限チェック
        if not tenant.is_within_limits('sites'):
            raise ValidationError(
                f"サイト数の上限（{tenant.max_sites}個）に達しています。"
                f"プランをアップグレードしてください。"
            )
        
        serializer.save(tenant=tenant)
    
    @action(detail=False, methods=['get'])
    def limits(self, request):
        """テナントの制限情報を返す"""
        tenant = request.tenant
        
        sites_count = Site.objects.filter(tenant=tenant, active=True).count()
        
        from datetime import datetime
        current_month = datetime.now().strftime('%Y-%m')
        conversions_count = ConversionOutput.objects.filter(
            setting__site__tenant=tenant,
            created_at__startswith=current_month
        ).count()
        
        return Response({
            'plan': tenant.plan,
            'sites': {
                'current': sites_count,
                'max': tenant.max_sites,
                'remaining': tenant.max_sites - sites_count,
            },
            'conversions': {
                'current': conversions_count,
                'max': tenant.max_conversions_per_month,
                'remaining': tenant.max_conversions_per_month - conversions_count,
            },
            'storage': {
                'used_mb': tenant.storage_used_mb,
                'max_mb': tenant.max_storage_mb,
                'remaining_mb': tenant.max_storage_mb - tenant.storage_used_mb,
            },
        })


class ConversionSettingViewSet(TenantFilteredViewSetMixin, viewsets.ModelViewSet):
    """変換設定のCRUD操作用ViewSet"""
    serializer_class = ConversionSettingSerializer
    
    def get_queryset(self):
        queryset = ConversionSetting.objects.filter(active=True)
        
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        
        # siteを通じてテナントでフィルタ
        queryset = queryset.filter(site__tenant=self.request.tenant)
        
        # site_idパラメータがあればさらにフィルタ
        site_id = self.request.query_params.get('site_id')
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        
        return queryset


class WordConversionView(APIView):
    """Wordファイルを変換するAPIView"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        tenant = request.tenant
        
        # 変換回数制限チェック
        if not tenant.is_within_limits('conversions'):
            return Response(
                {
                    "error": f"月間変換上限（{tenant.max_conversions_per_month}回）に達しました。"
                             f"プランをアップグレードしてください。",
                    "limit_reached": True,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # ストレージ制限チェック
        if not tenant.is_within_limits('storage'):
            return Response(
                {
                    "error": f"ストレージ上限（{tenant.max_storage_mb}MB）に達しました。"
                             f"古いファイルを削除するか、プランをアップグレードしてください。",
                    "limit_reached": True,
                },
                status=status.HTTP_507_INSUFFICIENT_STORAGE
            )
        
        # ... 既存の変換処理
        
        # 変換成功後、ストレージ使用量を更新
        file_size_mb = word_file.size / (1024 * 1024)
        tenant.storage_used_mb += file_size_mb
        tenant.save()
        
        # ... レスポンス返却
```

### Phase 4: マイグレーション（所要時間: 1時間）

#### ステップ4.1: マイグレーションファイルの作成

```bash
# マイグレーションファイル生成
docker compose exec backend python app/manage.py makemigrations

# マイグレーションの確認
docker compose exec backend python app/manage.py sqlmigrate api 0XXX
```

#### ステップ4.2: データ移行スクリプト

```python
# backend/api/migrations/0XXX_migrate_existing_data.py

from django.db import migrations


def create_default_tenant(apps, schema_editor):
    """既存データにデフォルトテナントを作成・割り当て"""
    Tenant = apps.get_model('api', 'Tenant')
    Site = apps.get_model('api', 'Site')
    User = apps.get_model('auth', 'User')
    TenantUser = apps.get_model('api', 'TenantUser')
    
    # デフォルトテナントを作成
    default_tenant, created = Tenant.objects.get_or_create(
        subdomain='default',
        defaults={
            'name': 'デフォルトテナント',
            'plan': 'enterprise',
            'max_sites': 999,
            'max_conversions_per_month': 99999,
            'is_active': True,
        }
    )
    
    # 既存のサイトをデフォルトテナントに割り当て
    Site.objects.filter(tenant__isnull=True).update(tenant=default_tenant)
    
    # 既存のユーザーをデフォルトテナントに割り当て
    for user in User.objects.all():
        TenantUser.objects.get_or_create(
            tenant=default_tenant,
            user=user,
            defaults={'role': 'owner'}
        )


class Migration(migrations.Migration):
    
    dependencies = [
        ('api', '0XXX_add_tenant_models'),
    ]
    
    operations = [
        migrations.RunPython(create_default_tenant),
    ]
```

#### ステップ4.3: マイグレーション実行

```bash
# バックアップ作成
docker compose exec db pg_dump -U postgres awa_webapp > backup_before_multitenant_$(date +%Y%m%d_%H%M%S).sql

# マイグレーション実行
docker compose exec backend python app/manage.py migrate

# 確認
docker compose exec backend python app/manage.py shell
>>> from api.models import Tenant, Site
>>> Tenant.objects.all()
>>> Site.objects.all()
```

---

## サブドメイン設定

### DNS設定

**ワイルドカードDNSレコード**:
```
*.awa-webapp.com  A  54.248.141.21
```

これにより以下のようなサブドメインが自動的に解決されます：
- company-a.awa-webapp.com → 54.248.141.21
- company-b.awa-webapp.com → 54.248.141.21

### Nginx設定

```nginx
# nginx/nginx.conf

server {
    listen 80;
    server_name ~^(?<subdomain>.+)\.awa-webapp\.com$;
    
    # サブドメインをヘッダーとして渡す
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant-Subdomain $subdomain;
        # ...
    }
    
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant-Subdomain $subdomain;
        # ...
    }
}
```

---

## 課金・プラン管理

### プラン定義

```python
# backend/api/plans.py

PLANS = {
    'free': {
        'name': 'フリープラン',
        'price': 0,
        'max_sites': 1,
        'max_conversions_per_month': 10,
        'max_file_size_mb': 5,
        'max_storage_mb': 100,
    },
    'basic': {
        'name': 'ベーシックプラン',
        'price': 5000,  # 円/月
        'max_sites': 3,
        'max_conversions_per_month': 100,
        'max_file_size_mb': 10,
        'max_storage_mb': 1000,
    },
    'pro': {
        'name': 'プロプラン',
        'price': 15000,  # 円/月
        'max_sites': 10,
        'max_conversions_per_month': 500,
        'max_file_size_mb': 20,
        'max_storage_mb': 5000,
    },
    'enterprise': {
        'name': 'エンタープライズプラン',
        'price': None,  # 要相談
        'max_sites': 9999,
        'max_conversions_per_month': 99999,
        'max_file_size_mb': 100,
        'max_storage_mb': 99999,
    },
}
```

### Stripe連携（将来的に）

```python
# backend/api/billing.py

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_customer(tenant, email):
    """Stripe顧客を作成"""
    customer = stripe.Customer.create(
        email=email,
        metadata={'tenant_id': tenant.id}
    )
    tenant.stripe_customer_id = customer.id
    tenant.save()
    return customer


def create_subscription(tenant, price_id):
    """サブスクリプションを作成"""
    subscription = stripe.Subscription.create(
        customer=tenant.stripe_customer_id,
        items=[{'price': price_id}],
    )
    return subscription
```

---

## テスト戦略

### テナント分離のテスト

```python
# backend/api/tests.py

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Tenant, TenantUser, Site


class TenantIsolationTestCase(TestCase):
    """テナント分離のテスト"""
    
    def setUp(self):
        # テナントA
        self.tenant_a = Tenant.objects.create(
            name="Tenant A",
            subdomain="tenant-a"
        )
        self.user_a = User.objects.create_user(
            username='user_a',
            password='password'
        )
        TenantUser.objects.create(
            tenant=self.tenant_a,
            user=self.user_a,
            role='owner'
        )
        self.site_a = Site.objects.create(
            tenant=self.tenant_a,
            name="Site A",
            url="site-a"
        )
        
        # テナントB
        self.tenant_b = Tenant.objects.create(
            name="Tenant B",
            subdomain="tenant-b"
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            password='password'
        )
        TenantUser.objects.create(
            tenant=self.tenant_b,
            user=self.user_b,
            role='owner'
        )
        self.site_b = Site.objects.create(
            tenant=self.tenant_b,
            name="Site B",
            url="site-b"
        )
    
    def test_tenant_a_cannot_see_tenant_b_data(self):
        """テナントAがテナントBのデータを見れないことを確認"""
        sites_for_tenant_a = Site.objects.filter(tenant=self.tenant_a)
        
        self.assertIn(self.site_a, sites_for_tenant_a)
        self.assertNotIn(self.site_b, sites_for_tenant_a)
    
    def test_tenant_limits(self):
        """テナント制限のテスト"""
        # Freeプランの制限
        tenant_free = Tenant.objects.create(
            name="Free Tenant",
            subdomain="free-tenant",
            plan='free',
            max_sites=1
        )
        
        # 1つ目のサイト作成（成功）
        Site.objects.create(
            tenant=tenant_free,
            name="Site 1",
            url="site-1"
        )
        
        # 制限チェック
        self.assertFalse(tenant_free.is_within_limits('sites'))
```

---

## まとめ

### 実装チェックリスト

- [ ] Tenantモデル・TenantUserモデルの作成
- [ ] 既存モデルへのtenant_idの追加
- [ ] TenantMiddlewareの実装
- [ ] ViewSetのテナントフィルタリング実装
- [ ] マイグレーション実行
- [ ] 既存データの移行
- [ ] サブドメイン設定（DNS）
- [ ] Nginx設定の更新
- [ ] プラン・制限のロジック実装
- [ ] テナント分離のテスト

### 工数見積もり

| タスク | 工数 |
|-------|------|
| モデル設計・実装 | 4時間 |
| Middleware実装 | 2時間 |
| ViewSet修正 | 4時間 |
| マイグレーション | 2時間 |
| サブドメイン設定 | 2時間 |
| テスト | 4時間 |
| **合計** | **18時間（約2.5日）** |

---

**最終更新日**: 2025年12月17日

