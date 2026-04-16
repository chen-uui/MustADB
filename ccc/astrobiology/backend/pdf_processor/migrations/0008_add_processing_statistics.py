# Generated migration for ProcessingStatistics model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_processor', '0007_processingtask_processinglog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessingStatistics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(help_text='统计日期', unique=True)),
                ('total_documents', models.IntegerField(default=0, help_text='总文档数')),
                ('successful_documents', models.IntegerField(default=0, help_text='成功处理文档数')),
                ('failed_documents', models.IntegerField(default=0, help_text='失败处理文档数')),
                ('avg_processing_time', models.FloatField(default=0.0, help_text='平均处理时间（秒）')),
                ('avg_confidence_score', models.FloatField(default=0.0, help_text='平均置信度分数')),
                ('total_meteorites', models.IntegerField(default=0, help_text='总陨石数')),
                ('total_organic_compounds', models.IntegerField(default=0, help_text='总有机化合物数')),
                ('total_insights', models.IntegerField(default=0, help_text='总科学洞察数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '处理统计',
                'verbose_name_plural': '处理统计',
                'db_table': 'pdf_processor_processingstatistics',
                'ordering': ['-date'],
            },
        ),
    ]