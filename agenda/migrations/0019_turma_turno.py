from django.db import migrations, models


def popular_turno(apps, schema_editor):
    Turma = apps.get_model("agenda", "Turma")
    mapa = {"M": "M", "V": "V", "N": "N", "I": "I"}
    for t in Turma.objects.all():
        nome = (t.nome_turma or "").strip()
        if not nome:
            continue
        sufixo = nome[-1].upper()
        if sufixo in mapa and not t.turno:
            t.turno = mapa[sufixo]
            t.save(update_fields=["turno"])


def reverter(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0018_alter_monitoria_nivel_ensino"),
    ]

    operations = [
        migrations.AddField(
            model_name="turma",
            name="turno",
            field=models.CharField(
                blank=True,
                choices=[
                    ("M", "Matutino"),
                    ("V", "Vespertino"),
                    ("N", "Noturno"),
                    ("I", "Integral"),
                ],
                default="",
                help_text="Período em que a turma estuda.",
                max_length=1,
                verbose_name="Turno",
            ),
        ),
        migrations.RunPython(popular_turno, reverter),
    ]
