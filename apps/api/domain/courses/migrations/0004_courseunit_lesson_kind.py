from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("courses", "0003_courseteachingexception")]

    operations = [
        migrations.AddField(
            model_name="courseunit",
            name="lesson_kind",
            field=models.CharField(
                choices=[
                    ("document", "Documento"),
                    ("mediacms_video", "Video MediaCMS"),
                    ("latex_source", "Archivo LaTeX (.tex)"),
                    ("markdown_source", "Archivo Markdown (.md)"),
                    ("pdf", "PDF"),
                    ("slides", "Diapositivas"),
                    ("audio", "Audio"),
                ],
                default="document",
                editable=False,
                max_length=20,
            ),
        )
    ]
