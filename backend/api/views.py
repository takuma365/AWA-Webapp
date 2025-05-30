import os
import json
import tempfile
import uuid
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.text import slugify
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Site, ConversionSetting, ConversionRule, ConversionOutput
from .serializers import (
    SiteSerializer, ConversionSettingSerializer,
    ConversionRuleSerializer, FileUploadSerializer, ConversionOutputSerializer
)
from .services.converter import WordToHtmlConverter
from pathlib import Path


class SiteViewSet(viewsets.ModelViewSet):
    """サイト情報のCRUD操作用ViewSet"""
    queryset = Site.objects.filter(active=True)
    serializer_class = SiteSerializer

    def get_queryset(self):
        """URLパラメータによるフィルタリングを行う"""
        queryset = super().get_queryset()
        url = self.request.query_params.get('url')
        if url:
            queryset = queryset.filter(url=url)
        return queryset

    def create(self, request, *args, **kwargs):
        """新しいサイト作成時にデフォルトの変換設定も自動生成"""
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == 201:
            # 作成されたサイトを取得
            site = Site.objects.get(pk=response.data['id'])
            
            # デフォルト変換設定を作成
            ConversionSetting.objects.create(
                site=site,
                name='デフォルト設定',
                css_class_prefix=f'{site.url}-',
                remove_empty_paragraphs=True,
                preserve_images=True,
                image_dir='images',
                active=True
            )
        
        return response


class ConversionSettingViewSet(viewsets.ModelViewSet):
    """変換設定のCRUD操作用ViewSet"""
    queryset = ConversionSetting.objects.filter(active=True)
    serializer_class = ConversionSettingSerializer

    def get_queryset(self):
        """サイトIDによるフィルタリングを行う"""
        queryset = super().get_queryset()
        site_id = self.request.query_params.get('site_id')
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        return queryset


class ConversionRuleViewSet(viewsets.ModelViewSet):
    """変換ルールのCRUD操作用ViewSet"""
    queryset = ConversionRule.objects.filter(active=True)
    serializer_class = ConversionRuleSerializer

    def get_queryset(self):
        """設定IDによるフィルタリングを行う"""
        queryset = super().get_queryset()
        setting_id = self.request.query_params.get('setting_id')
        if setting_id:
            queryset = queryset.filter(setting_id=setting_id)
        return queryset


class ConversionOutputViewSet(viewsets.ReadOnlyModelViewSet):
    """変換出力結果の参照用ViewSet (読み取り専用)"""
    queryset = ConversionOutput.objects.all().order_by('-created_at')
    serializer_class = ConversionOutputSerializer

    def get_queryset(self):
        """設定IDによるフィルタリングを行う"""
        queryset = super().get_queryset()
        setting_id = self.request.query_params.get('setting_id')
        if setting_id:
            queryset = queryset.filter(setting_id=setting_id)
        return queryset


class WordConversionView(APIView):
    """Wordファイルを変換するAPIView"""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        """
        WordファイルをアップロードしてHTML変換を行う
        """
        serializer = FileUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # バリデーション済みデータを取得
        word_file = serializer.validated_data['file']
        
        # ファイル拡張子の確認
        name, ext = os.path.splitext(word_file.name)
        if ext.lower() not in ['.docx']:
            return Response(
                {"error": "サポートされていないファイル形式です。.docx形式のみ対応しています。"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 一時保存先の確認
            temp_dir = Path(settings.UPLOAD_TEMP_DIR)
            if not temp_dir.exists():
                temp_dir.mkdir(parents=True, exist_ok=True)
                
            # 変換設定の取得
            setting = serializer.get_conversion_setting()
            
            # 変換処理の実行
            converter = WordToHtmlConverter(setting)
            html_content, images = converter.convert(word_file)
            
            # HTMLの保存先ディレクトリの確認
            html_dir = Path(settings.UPLOAD_HTML_DIR)
            if not html_dir.exists():
                html_dir.mkdir(parents=True, exist_ok=True)
            
            # ファイル名の生成
            safe_filename = slugify(os.path.splitext(word_file.name)[0]) or 'converted'
            unique_filename = f"{safe_filename}_{uuid.uuid4().hex[:8]}.html"
            html_path = html_dir / unique_filename
            
            # HTMLをファイルに保存
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 変換結果をデータベースに保存
            output = ConversionOutput.objects.create(
                setting=setting,
                original_filename=word_file.name,
                html_content=html_content,
                html_path=str(html_path.relative_to(settings.BASE_DIR))
            )
            
            # レスポンスの作成
            response_data = {
                "id": output.id,
                "original_filename": output.original_filename,
                "message": "変換が完了しました。",
                "images": images
            }
            
            # XMLファイルの情報が利用可能であればレスポンスに追加
            if hasattr(converter, 'parsed_data') and 'xml_files' in converter.parsed_data:
                xml_info = converter.parsed_data['xml_files']
                # 相対パスに変換する
                if 'directory' in xml_info:
                    xml_info['relative_directory'] = os.path.relpath(xml_info['directory'], settings.BASE_DIR)
                response_data['xml_files'] = xml_info
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            
            return Response(
                {"error": f"変換処理中にエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
class WordDownloadView(APIView):
    """変換したHTMLをダウンロードするAPIView"""
    
    def get(self, request, *args, **kwargs):
        """
        指定されたIDのHTMLをダウンロードする
        """
        output_id = request.query_params.get('id')
        
        if not output_id:
            return Response(
                {"error": "出力IDが指定されていません。"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 変換出力を取得
            output = get_object_or_404(ConversionOutput, pk=output_id)
            
            # HTMLコンテンツを取得
            html_content = output.html_content
            
            # ファイル名の整形
            safe_filename = slugify(output.original_filename) or 'converted'
            if not safe_filename.endswith('.html'):
                safe_filename += '.html'
            
            # 完全なHTMLドキュメントを作成
            full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>変換済みドキュメント</title>
</head>
<body>
{html_content}
</body>
</html>"""
            
            # レスポンスの作成
            response = HttpResponse(full_html, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {"error": f"ダウンロード処理中にエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """
        受け取ったHTMLを整形してダウンロードさせる（後方互換性のため維持）
        """
        # HTMLコンテンツを取得
        html_content = request.data.get('html')
        filename = request.data.get('filename', 'converted')
        
        if not html_content:
            return Response(
                {"error": "HTMLコンテンツが指定されていません。"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ファイル名の整形
        safe_filename = slugify(filename) or 'converted'
        if not safe_filename.endswith('.html'):
            safe_filename += '.html'
        
        # 完全なHTMLドキュメントを作成
        full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>変換済みドキュメント</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        # レスポンスの作成
        response = HttpResponse(full_html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        
        return response 