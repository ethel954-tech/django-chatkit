# Generated migration for Status models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True, max_length=500)),
                ('media', models.FileField(blank=True, help_text='Image or video', null=True, upload_to='statuses/%Y/%m/%d/')),
                ('media_type', models.CharField(blank=True, choices=[('image', 'Image'), ('video', 'Video')], max_length=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='statuses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StatusView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views', to='status.status')),
                ('viewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='viewed_statuses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['viewed_at'],
                'unique_together': {('status', 'viewer')},
            },
        ),
        migrations.CreateModel(
            name='StatusHidden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hidden_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hidden_from_users', to='status.status')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hidden_statuses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('status', 'user')},
            },
        ),
        migrations.AddIndex(
            model_name='status',
            index=models.Index(fields=['expires_at', 'user'], name='status_stat_expires_idx'),
        ),
    ]
