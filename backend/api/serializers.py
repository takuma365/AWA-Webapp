from rest_framework import serializers
from .models import Site, ConversionSetting, ConversionRule, ConversionOutput


class ConversionRuleSerializer(serializers.ModelSerializer):
    """変換ルールシリアライザ"""
    class Meta:
        model = ConversionRule
        fields = [
            'id', 'name', 'rule_type', 'source_selector',
            'target_value', 'priority', 'active'
        ]


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
        fields = ['id', 'name', 'code', 'active', 'conversion_settings']


class FileUploadSerializer(serializers.Serializer):
    """ファイルアップロードシリアライザ"""
    file = serializers.FileField(required=True)
    setting_id = serializers.IntegerField(required=True)


class ConversionOutputSerializer(serializers.ModelSerializer):
    """変換出力結果シリアライザ"""
    class Meta:
        model = ConversionOutput
        fields = ['id', 'original_filename', 'created_at', 'setting']
        read_only_fields = ['id', 'created_at'] 