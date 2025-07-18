from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='client_domain',
            field=models.CharField(
                verbose_name='クライアントサイトのドメイン',
                max_length=255,
                blank=True,
                help_text='例: https://client.com'
            ),
        ),
    ] 