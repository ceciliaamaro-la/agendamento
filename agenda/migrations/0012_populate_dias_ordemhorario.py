from django.db import migrations


DIAS = [
    (1, "Domingo"),
    (2, "Segunda-feira"),
    (3, "Terça-feira"),
    (4, "Quarta-feira"),
    (5, "Quinta-feira"),
    (6, "Sexta-feira"),
    (7, "Sábado"),
]

ORDENS = [
    "1ª Aula",
    "2ª Aula",
    "3ª Aula",
    "4ª Aula",
    "5ª Aula",
    "6ª Aula",
    "Intervalo",
    "Almoço",
    "Lanche",
]


def populate(apps, schema_editor):
    Dias = apps.get_model("agenda", "Dias")
    OrdemHorario = apps.get_model("agenda", "OrdemHorario")

    for ordem, nome in DIAS:
        Dias.objects.get_or_create(ordem=ordem, defaults={"dias": nome})

    for nome in ORDENS:
        OrdemHorario.objects.get_or_create(ordem=nome)


def depopulate(apps, schema_editor):
    apps.get_model("agenda", "Dias").objects.filter(
        dias__in=[d[1] for d in DIAS]
    ).delete()
    apps.get_model("agenda", "OrdemHorario").objects.filter(
        ordem__in=ORDENS
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0011_conexao_fk_to_o2o"),
    ]

    operations = [
        migrations.RunPython(populate, depopulate),
    ]
