# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pdf_processor', '0008_add_processing_statistics'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfdocument',
            name='review_status',
            field=models.CharField(choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')], default='approved', max_length=20, verbose_name='审核状态'),
        ),
        migrations.AddField(
            model_name='pdfdocument',
            name='review_notes',
            field=models.TextField(blank=True, null=True, verbose_name='审核备注'),
        ),
        migrations.AddField(
            model_name='pdfdocument',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_pdfs', to=settings.AUTH_USER_MODEL, verbose_name='审核人'),
        ),
        migrations.AddField(
            model_name='pdfdocument',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='审核时间'),
        ),
        migrations.AddField(
            model_name='pdfdocument',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_pdfs', to=settings.AUTH_USER_MODEL, verbose_name='上传人'),
        ),
        migrations.AddIndex(
            model_name='pdfdocument',
            index=models.Index(fields=['review_status'], name='pdf_doc_review_status_idx'),
        ),
        migrations.AddIndex(
            model_name='pdfdocument',
            index=models.Index(fields=['uploaded_by'], name='pdf_doc_uploaded_by_idx'),
        ),
    ]

