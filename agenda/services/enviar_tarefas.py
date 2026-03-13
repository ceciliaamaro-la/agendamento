from agenda.models import AgendaEvento, Turma, Aluno, WhatsAppEnvio
from evolution.app import enviar_texto

def enviar_tarefas():

    eventos = AgendaEvento.objects.filter(enviado_whatsapp=False)

    for evento in eventos:

        turma = Turma.objects.filter(nome_turma=evento.tipo).first()

        if not turma:
            continue

        alunos = Aluno.objects.filter(turma=turma)

        for aluno in alunos:

            numero = aluno.telefone

            if WhatsAppEnvio.objects.filter(
                evento=evento,
                numero_destino=numero
            ).exists():
                continue

            mensagem = f"""
📚 *Nova tarefa*

Turma: {turma.nome_turma}

{evento.titulo}

{evento.descricao}

Data: {evento.data}
"""

            enviar_texto(numero, mensagem)

            WhatsAppEnvio.objects.create(
                evento=evento,
                numero_destino=numero,
                hash_evento=evento.hash
            )

        evento.enviado_whatsapp = True
        evento.save()