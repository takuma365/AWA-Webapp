from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0003_merge_20250716_1517'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='client_domain_omit',
            field=models.BooleanField(
                verbose_name='クライアントドメイン省略フラグ',
                default=False,
                help_text='内部リンク時にドメインURLを省略するか'
            ),
        ),
    ] 