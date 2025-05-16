from django.contrib import admin
from .models import Site, ConversionSetting, ConversionRule


class ConversionRuleInline(admin.TabularInline):
    """変換設定に対する変換ルールをインラインで表示するためのクラス"""
    model = ConversionRule
    extra = 1


class ConversionSettingInline(admin.TabularInline):
    """サイトに対する変換設定をインラインで表示するためのクラス"""
    model = ConversionSetting
    extra = 1


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """サイト管理画面の設定"""
    list_display = ('name', 'code', 'active', 'created_at', 'updated_at')
    list_filter = ('active',)
    search_fields = ('name', 'code')
    inlines = [ConversionSettingInline]


@admin.register(ConversionSetting)
class ConversionSettingAdmin(admin.ModelAdmin):
    """変換設定管理画面の設定"""
    list_display = ('name', 'site', 'active', 'created_at', 'updated_at')
    list_filter = ('active', 'site')
    search_fields = ('name', 'site__name')
    inlines = [ConversionRuleInline]


@admin.register(ConversionRule)
class ConversionRuleAdmin(admin.ModelAdmin):
    """変換ルール管理画面の設定"""
    list_display = ('name', 'setting', 'rule_type', 'priority', 'active')
    list_filter = ('active', 'rule_type', 'setting__site')
    search_fields = ('name', 'setting__name', 'source_selector') 