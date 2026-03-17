import threading
import logging
from datetime import datetime

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger(__name__)

_status = {
    'rodando': False,
    'ultima_execucao': None,
    'salvos': 0,
    'ignorados': 0,
    'conexoes_processadas': 0,
    'erro': None,
}
_status_lock = threading.Lock()


def _executar_sync():
    global _status
    try:
        from agenda.services.sync_agenda import sincronizar_agenda_com_resultado
        resultado = sincronizar_agenda_com_resultado()
        with _status_lock:
            _status['rodando'] = False
            _status['salvos'] = resultado.get('salvos', 0)
            _status['ignorados'] = resultado.get('ignorados', 0)
            _status['conexoes_processadas'] = resultado.get('conexoes', 0)
            _status['erro'] = None
            _status['ultima_execucao'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        logger.info(f"✅ Robô concluído: {resultado}")
    except Exception as e:
        logger.error(f"❌ Erro no robô: {e}")
        with _status_lock:
            _status['rodando'] = False
            _status['erro'] = str(e)
            _status['ultima_execucao'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')


@staff_member_required
def executar_robo(request):
    with _status_lock:
        if _status['rodando']:
            return JsonResponse({'ok': False, 'mensagem': 'O robô já está em execução.'})
        _status['rodando'] = True
        _status['erro'] = None
        _status['salvos'] = 0
        _status['ignorados'] = 0
        _status['conexoes_processadas'] = 0

    t = threading.Thread(target=_executar_sync, daemon=True)
    t.start()
    return JsonResponse({'ok': True, 'mensagem': 'Robô iniciado!'})


@staff_member_required
def status_robo(request):
    with _status_lock:
        return JsonResponse(dict(_status))
