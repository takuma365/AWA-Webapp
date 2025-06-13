from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRFのルーター設定
router = DefaultRouter()
router.register(r'sites', views.SiteViewSet)
router.register(r'settings', views.ConversionSettingViewSet)
router.register(r'rules', views.ConversionRuleViewSet)
router.register(r'outputs', views.ConversionOutputViewSet)

# URLパターン
urlpatterns = [
    # DRFのルーターによるエンドポイント
    path('', include(router.urls)),
    
    # カスタムAPIエンドポイント
    path('convert/', views.WordConversionView.as_view(), name='convert'),
    path('download/', views.WordDownloadView.as_view(), name='download'),
    path('generate-html/', views.GenerateHtmlView.as_view(), name='generate_html'),
] 