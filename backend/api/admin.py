from django.contrib import admin
from .models import Site, ConversionSetting, ConversionRule


class ConversionRuleInline(admin.TabularInline):
    """変換設定に対する変換ルールをインラインで表示するためのクラス"""
    model = ConversionRule
    extra = 1
    fields = ('section', 'tag', 'word_style', 'bold', 'marker', 'prefix_text', 'suffix_text', 'active')
    readonly_fields = ('created_at', 'updated_at')


class ConversionSettingInline(admin.TabularInline):
    """サイトに対する変換設定をインラインで表示するためのクラス"""
    model = ConversionSetting
    extra = 1


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """サイト管理画面の設定"""
    list_display = ('name', 'url', 'active', 'created_at', 'updated_at')
    list_filter = ('active',)
    search_fields = ('name', 'url')
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
    list_display = ('section', 'setting', 'word_style', 'tag', 'bold', 'marker', 'active')
    list_filter = ('active', 'section', 'word_style', 'bold', 'marker', 'setting__site')
    search_fields = ('section', 'setting__name', 'tag', 'word_style')
    list_editable = ('active',)
    ordering = ('setting', 'section') 