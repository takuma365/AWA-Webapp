from rest_framework import serializers
from .models import Site, ConversionSetting, ConversionRule, ConversionOutput


class ConversionRuleSerializer(serializers.ModelSerializer):
    """変換ルールシリアライザ"""
    class Meta:
        model = ConversionRule
        fields = [
            'id', 'setting', 'section', 'tag', 'word_style', 'bold', 'marker',
            'prefix_text', 'suffix_text', 'active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'setting': {'required': True},
            'tag': {'required': True},
            'word_style': {'required': True},
            'prefix_text': {'required': False, 'allow_blank': True, 'allow_null': True},
            'suffix_text': {'required': False, 'allow_blank': True, 'allow_null': True},
            'bold': {'required': False},
            'marker': {'required': False},
        }


class ConversionSettingSerializer(serializers.ModelSerializer):
    """変換設定シリアライザ"""
    rules = ConversionRuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = ConversionSetting
        fields = [
            'id', 'name', 'css_class_prefix', 'remove_empty_paragraphs',
            'preserve_images', 'image_dir', 'active', 'rules'
        ]


class SiteSerializer(serializers.ModelSerializer):
    """サイトシリアライザ"""
    conversion_settings = ConversionSettingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Site
        fields = ['id', 'name', 'url', 'active', 'conversion_settings']


class FileUploadSerializer(serializers.Serializer):
    """ファイルアップロードシリアライザ"""
    file = serializers.FileField(required=True)
    site_url = serializers.CharField(required=True, help_text='サイトのURL')

    def validate_site_url(self, value):
        """サイトURLの存在確認"""
        try:
            site = Site.objects.get(url=value, active=True)
            return value
        except Site.DoesNotExist:
            raise serializers.ValidationError('指定されたサイトが見つかりません。')

    def get_conversion_setting(self):
        """サイトのデフォルト変換設定を取得"""
        site_url = self.validated_data['site_url']
        site = Site.objects.get(url=site_url, active=True)
        
        # デフォルト変換設定を取得（なければ作成）
        setting, created = ConversionSetting.objects.get_or_create(
            site=site,
            name='デフォルト設定',
            defaults={
                'css_class_prefix': f'{site.url}-',
                'remove_empty_paragraphs': True,
                'preserve_images': True,
                'image_dir': 'images',
                'active': True
            }
        )
        return setting


class ConversionOutputSerializer(serializers.ModelSerializer):
    """変換出力結果シリアライザ"""
    class Meta:
        model = ConversionOutput
        fields = ['id', 'original_filename', 'created_at', 'setting']
        read_only_fields = ['id', 'created_at'] 