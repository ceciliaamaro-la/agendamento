"""Períodos (Ordem de Horário) podem ser GLOBAIS (escola=None) ou
ESPECÍFICOS de uma escola (escola=X).

- Períodos GLOBAIS: visíveis em todas as escolas, gerenciados apenas por
  super-administrador.
- Períodos ESPECÍFICOS: visíveis e gerenciados pelo admin_escola da escola
  correspondente.
- Coordenador: somente leitura.
"""

from collections import OrderedDict

from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import OrdemHorario
from ..forms import OrdemHorarioForm
from ..services.escopo import (
    admin_estrito_required, bloquear_alunos_responsaveis, _negar,
    is_superadmin, is_coordenador, is_admin_escola,
    escolas_administradas, escolas_do_usuario, pode_administrar_escola,
)


def _ordens_visiveis(user):
    """OrdemHorario que o usuário pode VER:
    - Globais (escola__isnull=True) — sempre visíveis
    - Específicas de escolas que ele tem acesso
    """
    if is_superadmin(user):
        return OrdemHorario.objects.all()
    return OrdemHorario.objects.filter(
        Q(escola__isnull=True) | Q(escola__in=escolas_do_usuario(user))
    )


def _pode_editar_ordem(user, ordem):
    """Regras:
    - Coordenador NÃO edita nada.
    - Períodos GLOBAIS (escola=None) só superadmin edita.
    - Períodos ESPECÍFICOS: admin_escola da escola correspondente edita.
    """
    if is_coordenador(user):
        return False
    if ordem.escola_id is None:
        return is_superadmin(user)
    return pode_administrar_escola(user, ordem.escola)


@bloquear_alunos_responsaveis
def ordem_list(request):
    ordens = _ordens_visiveis(request.user).select_related("escola").order_by(
        "escola__nome_escola", "turno", "posicao", "id"
    )

    rotulos = dict(OrdemHorario.TURNO_CHOICES)
    # Estrutura: {(escola_nome, escola_id_or_None): {turno: {rotulo, itens}}}
    escolas_grupo = OrderedDict()

    # Reúne primeiro itens globais
    chave_global = ("(Global) Períodos comuns", None)
    escolas_grupo[chave_global] = OrderedDict()
    for sigla in ("M", "V", "N", "I", ""):
        escolas_grupo[chave_global][sigla] = {
            "rotulo": rotulos.get(sigla, "Comum a todos os turnos"),
            "itens": [],
        }

    for o in ordens:
        if o.escola_id is None:
            chave = chave_global
        else:
            chave = (o.escola.nome_escola, o.escola_id)
            if chave not in escolas_grupo:
                escolas_grupo[chave] = OrderedDict()
                for sigla in ("M", "V", "N", "I", ""):
                    escolas_grupo[chave][sigla] = {
                        "rotulo": rotulos.get(sigla, "Comum a todos os turnos"),
                        "itens": [],
                    }
        sigla = o.turno or ""
        escolas_grupo[chave][sigla]["itens"].append(o)

    # Remove blocos/grupos vazios
    grupos_finais = OrderedDict()
    for chave_escola, blocos in escolas_grupo.items():
        blocos_nao_vazios = OrderedDict(
            (k, v) for k, v in blocos.items() if v["itens"]
        )
        if blocos_nao_vazios:
            grupos_finais[chave_escola] = blocos_nao_vazios

    pode_admin = (
        is_superadmin(request.user)
        or (is_admin_escola(request.user) and not is_coordenador(request.user))
    )

    return render(request, "diario/ordem_horario/list.html", {
        "ordens": ordens,
        "grupos_por_escola": grupos_finais,
        "pode_admin": pode_admin,
        "is_superadmin": is_superadmin(request.user),
    })


@admin_estrito_required
def ordem_create(request):
    form = OrdemHorarioForm(request.POST or None, request_user=request.user)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        # Validação de escopo: se escola foi escolhida, tem que ser administrada
        if obj.escola_id is not None and not pode_administrar_escola(request.user, obj.escola):
            return _negar(request, "Você não administra essa escola.")
        # Apenas superadmin pode criar período global
        if obj.escola_id is None and not is_superadmin(request.user):
            return _negar(request, "Apenas super-administrador pode criar período GLOBAL.")
        obj.save()
        messages.success(request, "Período cadastrado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Novo Período"})


@admin_estrito_required
def ordem_update(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if not _pode_editar_ordem(request.user, ordem):
        return _negar(request, "Sem permissão para editar este período.")
    form = OrdemHorarioForm(request.POST or None, instance=ordem, request_user=request.user)
    if request.method == "POST" and form.is_valid():
        nova = form.save(commit=False)
        if nova.escola_id is not None and not pode_administrar_escola(request.user, nova.escola):
            return _negar(request, "Escola fora do seu escopo.")
        if nova.escola_id is None and not is_superadmin(request.user):
            return _negar(request, "Apenas super-administrador pode salvar período GLOBAL.")
        nova.save()
        messages.success(request, "Período atualizado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Editar Período"})


@admin_estrito_required
def ordem_delete(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if not _pode_editar_ordem(request.user, ordem):
        return _negar(request, "Sem permissão para excluir este período.")
    if request.method == "POST":
        ordem.delete()
        messages.success(request, "Período excluído.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/confirm_delete.html", {"obj": ordem, "titulo": "Excluir Período"})


def _normalizar_posicoes(qs):
    """Garante que os períodos do queryset tenham posições sequenciais 1..N
    respeitando a ordem atual (posicao, id). Aplica-se ao escopo dado."""
    for i, o in enumerate(qs.order_by("posicao", "id"), start=1):
        if o.posicao != i:
            OrdemHorario.objects.filter(pk=o.pk).update(posicao=i)


@admin_estrito_required
def ordem_mover(request, pk, direcao):
    """Move um período para cima ou para baixo trocando posições com o vizinho
    DENTRO da mesma escola e turno (escopo isolado)."""
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if not _pode_editar_ordem(request.user, ordem):
        return _negar(request, "Sem permissão para mover este período.")
    irmaos = OrdemHorario.objects.filter(escola=ordem.escola, turno=ordem.turno)
    _normalizar_posicoes(irmaos)
    ordem.refresh_from_db()
    if direcao == "cima":
        vizinho = irmaos.filter(posicao__lt=ordem.posicao).order_by("-posicao").first()
    else:
        vizinho = irmaos.filter(posicao__gt=ordem.posicao).order_by("posicao").first()
    if vizinho:
        p1, p2 = ordem.posicao, vizinho.posicao
        OrdemHorario.objects.filter(pk=ordem.pk).update(posicao=p2)
        OrdemHorario.objects.filter(pk=vizinho.pk).update(posicao=p1)
    return redirect("cal:ordem_list")
