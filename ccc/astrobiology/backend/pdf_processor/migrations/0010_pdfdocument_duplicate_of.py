# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pdf_processor", "0009_add_review_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="pdfdocument",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicate_children",
                to="pdf_processor.pdfdocument",
            ),
        ),
    ]
