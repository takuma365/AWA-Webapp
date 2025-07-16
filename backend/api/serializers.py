from rest_framework import serializers
from .models import Site, ConversionSetting, ConversionRule, ConversionOutput

class ConversionRuleSerializer(serializers.ModelSerializer):
    """変換ルールシリアライザ"""
    class Meta:
        model = ConversionRule
        fields = [
            'id', 'setting', 'section', 'tag', 'word_style', 'bold', 'marker',
            'prefix_text', 'suffix_text', 'split_on_period', 'active', 'created_at', 'updated_at'
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
            'split_on_period': {'required': False},
        }


class ConversionSettingSerializer(serializers.ModelSerializer):
    rules = serializers.SerializerMethodField()

    class Meta:
        model = ConversionSetting
        fields = [
            'id', 'name', 'css_class_prefix', 'remove_empty_paragraphs',
            'preserve_images', 'image_dir', 'active', 'rules'
        ]

    def get_rules(self, obj):
        rules = obj.rules.filter(active=True)
        return ConversionRuleSerializer(rules, many=True).data


class SiteSerializer(serializers.ModelSerializer):
    """サイトシリアライザ"""
    conversion_settings = ConversionSettingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Site
        fields = ['id', 'name', 'url', 'active', 'conversion_settings']


class FileUploadSerializer(serializers.Serializer):
    """ファイルアップロードシリアライザ"""
    file = serializers.FileField(required=True)
    setting_id = serializers.IntegerField(required=True, help_text='変換設定のID')

    def validate_setting_id(self, value):
        """変換設定IDの存在確認"""
        try:
            setting = ConversionSetting.objects.get(id=value, active=True)
            return value
        except ConversionSetting.DoesNotExist:
            raise serializers.ValidationError('指定された変換設定が見つかりません。')

    def get_conversion_setting(self):
        """変換設定を取得"""
        setting_id = self.validated_data['setting_id']
        setting = ConversionSetting.objects.get(id=setting_id, active=True)
        return setting


class ConversionOutputSerializer(serializers.ModelSerializer):
    """変換出力結果シリアライザ"""
    class Meta:
        model = ConversionOutput
        fields = ['id', 'original_filename', 'created_at', 'setting']
        read_only_fields = ['id', 'created_at'] 