"""
古い変換結果を削除するDjangoコマンド

使用方法:
    python manage.py delete_old_conversions --days=7

cronで定期実行する場合:
    # 毎日午前3時に7日以上前のデータを削除
    0 3 * * * cd /home/ubuntu/AWA-Webapp/backend && python app/manage.py delete_old_conversions --days=7
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import ConversionOutput
import os


class Command(BaseCommand):
    help = '指定日数以上前の変換結果を削除します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='削除対象とする日数（デフォルト: 7日）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には削除せず、削除対象のみ表示'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # 削除対象の日時を計算
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # 古い変換結果を取得
        old_conversions = ConversionOutput.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = old_conversions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'{days}日以上前の変換結果はありません。'
                )
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'\n{days}日以上前の変換結果: {count}件\n'
            )
        )
        
        # 削除対象の詳細を表示
        for conversion in old_conversions[:10]:  # 最大10件表示
            age_days = (timezone.now() - conversion.created_at).days
            self.stdout.write(
                f'  - ID: {conversion.id}, '
                f'ファイル: {conversion.original_filename}, '
                f'作成日: {conversion.created_at.strftime("%Y-%m-%d %H:%M")}, '
                f'経過日数: {age_days}日'
            )
        
        if count > 10:
            self.stdout.write(f'  ... 他 {count - 10}件')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n[DRY RUN] 実際には削除されませんでした。\n'
                    '--dry-run を外して実行すると削除されます。'
                )
            )
            return
        
        # 実際に削除
        try:
            # HTMLファイルも削除
            deleted_files = 0
            for conversion in old_conversions:
                if conversion.html_path and os.path.exists(conversion.html_path):
                    try:
                        os.remove(conversion.html_path)
                        deleted_files += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f'ファイル削除エラー: {conversion.html_path} - {str(e)}'
                            )
                        )
            
            # DB から削除
            deleted_count, _ = old_conversions.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ 完了:\n'
                    f'  - DBレコード削除: {deleted_count}件\n'
                    f'  - HTMLファイル削除: {deleted_files}件'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'エラーが発生しました: {str(e)}'
                )
            )
            raise

