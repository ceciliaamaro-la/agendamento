from django.db import migrations, models


def inferir_turno(apps, schema_editor):
    """Infere turno pelo horário de início:
       < 12:00 → Matutino; >= 12:00 e < 18:00 → Vespertino; >= 18:00 → Noturno.
       Períodos sem horário (intervalo etc.) ficam em branco."""
    OrdemHorario = apps.get_model("agenda", "OrdemHorario")
    for o in OrdemHorario.objects.all():
        if o.turno or not o.inicio:
            continue
        h = o.inicio.hour
        if h < 12:
            o.turno = "M"
        elif h < 18:
            o.turno = "V"
        else:
            o.turno = "N"
        o.save(update_fields=["turno"])


def reverter(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0019_turma_turno"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordemhorario",
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
                help_text="Deixe em branco para períodos comuns a todos os turnos (ex.: Intervalo).",
                max_length=1,
                verbose_name="Turno",
            ),
        ),
        migrations.AlterModelOptions(
            name="ordemhorario",
            options={
                "ordering": ["turno", "posicao", "id"],
                "verbose_name": "Ordem de Horário",
                "verbose_name_plural": "Ordens de Horário",
            },
        ),
        migrations.RunPython(inferir_turno, reverter),
    ]
