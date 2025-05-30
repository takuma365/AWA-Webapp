from django.db import models
from django.utils.translation import gettext_lazy as _


class Site(models.Model):
    """サイト設定モデル"""
    name = models.CharField(_('サイト名'), max_length=255)
    code = models.CharField(_('サイトコード'), max_length=50, unique=True)
    active = models.BooleanField(_('有効'), default=True)
    created_at = models.DateTimeField(_('作成日時'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新日時'), auto_now=True)

    class Meta:
        verbose_name = _('サイト')
        verbose_name_plural = _('サイト')
        ordering = ['name']

    def __str__(self):
        return self.name


class ConversionSetting(models.Model):
    """変換設定モデル"""
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='conversion_settings',
        verbose_name=_('サイト')
    )
    name = models.CharField(_('設定名'), max_length=255)
    css_class_prefix = models.CharField(_('CSSクラスプレフィックス'), max_length=50, blank=True)
    remove_empty_paragraphs = models.BooleanField(_('空の段落を削除'), default=True)
    preserve_images = models.BooleanField(_('画像を保持'), default=True)
    image_dir = models.CharField(_('画像ディレクトリ'), max_length=255, blank=True)
    active = models.BooleanField(_('有効'), default=True)
    created_at = models.DateTimeField(_('作成日時'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新日時'), auto_now=True)

    class Meta:
        verbose_name = _('変換設定')
        verbose_name_plural = _('変換設定')
        ordering = ['site', 'name']

    def __str__(self):
        return f"{self.site.name} - {self.name}"


class ConversionRule(models.Model):
    """変換ルールモデル"""
    RULE_TYPE_CHOICES = [
        ('tag_replace', _('タグ置換')),
        ('class_add', _('クラス追加')),
        ('attribute_add', _('属性追加')),
        ('custom', _('カスタム処理')),
    ]
    
    setting = models.ForeignKey(
        ConversionSetting,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name=_('変換設定')
    )
    name = models.CharField(_('ルール名'), max_length=255)
    rule_type = models.CharField(_('ルールタイプ'), max_length=20, choices=RULE_TYPE_CHOICES)
    source_selector = models.CharField(_('対象セレクタ'), max_length=255)
    target_value = models.CharField(_('変換値'), max_length=255, blank=True)
    priority = models.IntegerField(_('優先度'), default=0)
    active = models.BooleanField(_('有効'), default=True)
    
    class Meta:
        verbose_name = _('変換ルール')
        verbose_name_plural = _('変換ルール')
        ordering = ['setting', 'priority']
    
    def __str__(self):
        return f"{self.setting} - {self.name}"


class ConversionOutput(models.Model):
    """変換出力結果を保存するモデル"""
    setting = models.ForeignKey(ConversionSetting, on_delete=models.CASCADE, related_name='outputs')
    original_filename = models.CharField(max_length=255)
    html_content = models.TextField()
    html_path = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.original_filename} - {self.created_at}" 