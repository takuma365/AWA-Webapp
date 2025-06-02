from django.db import models
from django.utils.translation import gettext_lazy as _


class Site(models.Model):
    """サイト設定モデル"""
    name = models.CharField(_('サイト名'), max_length=255)
    url = models.CharField(_('URL'), max_length=100, unique=True, help_text=_('サイトのURL（英小文字）'), null=True, blank=True)
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
    
    SECTION_CHOICES = [
        ('タイトル', _('タイトル')),
        ('目次', _('目次')),
        ('大見出し', _('大見出し')),
        ('中見出し', _('中見出し')),
        ('小見出し', _('小見出し')),
        ('内部リンク', _('内部リンク')),
        ('外部リンク', _('外部リンク')),
        ('太字', _('太字')),
        ('ハイライト', _('ハイライト')),
        ('赤字', _('赤字')),
        ('箱の枠', _('箱の枠')),
        ('箱内テキスト（中点）', _('箱内テキスト（中点）')),
        ('箱内リンクテキスト（中点）', _('箱内リンクテキスト（中点）')),
        ('箱内テキスト（番号）', _('箱内テキスト（番号）')),
        ('表', _('表')),
        ('テキスト', _('テキスト')),
        ('ショートコード', _('ショートコード')),
        ('文頭', _('文頭')),
        ('文末', _('文末')),
    ]
    
    WORD_STYLE_CHOICES = [
        ('見出し１', _('見出し１')),
        ('見出し２', _('見出し２')),
        ('見出し３', _('見出し３')),
        ('見出し４', _('見出し４')),
        ('標準', _('標準')),
        ('Wordに記載なし', _('Wordに記載なし')),
    ]
    
    setting = models.ForeignKey(
        ConversionSetting,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name=_('変換設定')
    )
    section = models.CharField(
        _('セクション'), 
        max_length=50, 
        choices=SECTION_CHOICES,
        default='大見出し'
    )
    tag = models.CharField(
        _('タグ'), 
        max_length=500, 
        help_text=_('HTML形式で入力（例: <h1></h1>）'),
        default='<p></p>'
    )
    word_style = models.CharField(
        _('Wordにおけるスタイル'), 
        max_length=50, 
        choices=WORD_STYLE_CHOICES,
        default='標準'
    )
    bold = models.BooleanField(_('太字'), default=False)
    marker = models.BooleanField(_('マーカー'), default=False)
    prefix_text = models.CharField(
        _('前にある文字列'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('改行は￥nで入力')
    )
    suffix_text = models.CharField(
        _('後ろにある文字列'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('改行は￥nで入力')
    )
    active = models.BooleanField(_('有効'), default=True)
    created_at = models.DateTimeField(_('作成日時'), auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(_('更新日時'), auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = _('変換ルール')
        verbose_name_plural = _('変換ルール')
        ordering = ['setting', 'section']
        unique_together = [['setting', 'section']]  # 同じ設定内で同じセクションは1つまで
    
    def __str__(self):
        return f"{self.setting} - {self.section}"


class ConversionOutput(models.Model):
    """変換出力結果を保存するモデル"""
    setting = models.ForeignKey(ConversionSetting, on_delete=models.CASCADE, related_name='outputs')
    original_filename = models.CharField(max_length=255)
    html_content = models.TextField()
    html_path = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.original_filename} - {self.created_at}" 