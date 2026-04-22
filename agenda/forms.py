from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import (
    Escola,
    Turma,
    Aluno,
    ConexaoAgenda,
    AgendaEvento,
    WhatsAppEnvio,
    TarefaCompleta,
    Materia,
    Professor,
    Livro,
    Dias,
    OrdemHorario,
    Horario,
    Aula,
    DiarioAluno,
)


# ===============================
# 👤 REGISTRO DE USUÁRIO
# ===============================

class UserRegisterForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Senha"
        }),
        label="Senha"
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nome de usuário"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "email@exemplo.com"
            }),
        }


# ===============================
# 👤 GERENCIAMENTO DE USUÁRIO
# ===============================

class UsuarioForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Senha"}),
        label="Senha",
    )
    confirmar_senha = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirmar senha"}),
        label="Confirmar Senha",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_staff"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        dados = super().clean()
        if dados.get("password") != dados.get("confirmar_senha"):
            raise forms.ValidationError("As senhas não coincidem.")
        return dados

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }


class UsuarioPasswordResetForm(forms.Form):

    nova_senha = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Nova senha"}),
        label="Nova Senha"
    )

    confirmar_senha = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirmar nova senha"}),
        label="Confirmar Senha"
    )

    def clean(self):
        dados = super().clean()
        if dados.get("nova_senha") != dados.get("confirmar_senha"):
            raise forms.ValidationError("As senhas não coincidem.")
        return dados


# ===============================
# 🎓 ESCOLA
# ===============================

class EscolaForm(forms.ModelForm):

    class Meta:
        model = Escola
        fields = ["nome_escola"]
        widgets = {
            "nome_escola": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg shadow-sm border-primary",
                    "placeholder": "Digite o nome da escola",
                    "style": "border-radius:10px;"
                }
            ),
        }
        labels = {"nome_escola": "Nome da Escola"}


# ===============================
# 🏫 TURMA
# ===============================

class TurmaForm(forms.ModelForm):

    class Meta:
        model = Turma
        fields = ["escola", "nome_turma"]
        widgets = {
            "escola": forms.Select(
                attrs={"class": "form-select shadow-sm border-success", "style": "border-radius:10px;"}
            ),
            "nome_turma": forms.TextInput(
                attrs={
                    "class": "form-control shadow-sm border-success",
                    "placeholder": "Ex: 7º Ano A",
                    "style": "border-radius:10px;"
                }
            ),
        }
        labels = {"escola": "Escola", "nome_turma": "Nome da Turma"}


# ===============================
# 👨‍🎓 ALUNO
# ===============================

class AlunoForm(forms.ModelForm):

    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False,
        label="Usuários vinculados (pai/mãe/responsável)",
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select shadow-sm border-info",
                "style": "border-radius:10px; min-height: 100px;",
                "size": "6",
            }
        ),
        help_text="Segure Ctrl (ou Cmd no Mac) para selecionar mais de um usuário."
    )

    class Meta:
        model = Aluno
        fields = ["turma", "nome_aluno", "usuarios", "telefone"]
        widgets = {
            "turma": forms.Select(
                attrs={"class": "form-select shadow-sm border-info", "style": "border-radius:10px;"}
            ),
            "nome_aluno": forms.TextInput(
                attrs={
                    "class": "form-control shadow-sm border-info",
                    "placeholder": "Nome completo do aluno",
                    "style": "border-radius:10px;"
                }
            ),
            "telefone": forms.TextInput(
                attrs={
                    "class": "form-control shadow-sm border-info",
                    "placeholder": "Ex: 5511999999999",
                    "style": "border-radius:10px;"
                }
            ),
        }
        labels = {
            "turma": "Turma",
            "nome_aluno": "Nome do Aluno",
            "telefone": "Telefone (WhatsApp)",
        }


# ===============================
# 🔗 CONEXÃO AGENDA
# ===============================

class ConexaoAgendaForm(forms.ModelForm):

    class Meta:
        model = ConexaoAgenda
        fields = ["turma", "login", "senha", "ativo"]
        widgets = {
            "turma": forms.Select(
                attrs={"class": "form-select shadow-sm border-warning", "style": "border-radius:10px;"}
            ),
            "login": forms.TextInput(
                attrs={
                    "class": "form-control shadow-sm border-warning",
                    "placeholder": "Login da plataforma",
                    "style": "border-radius:10px;"
                }
            ),
            "senha": forms.PasswordInput(
                attrs={
                    "class": "form-control shadow-sm border-warning",
                    "placeholder": "Senha da plataforma",
                    "style": "border-radius:10px;"
                }
            ),
            "ativo": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "transform: scale(1.3);"}
            ),
        }
        labels = {"turma": "Turma", "login": "Login", "senha": "Senha", "ativo": "Conexão Ativa"}


# ===============================
# 📅 EVENTO DA AGENDA
# ===============================

class AgendaEventoForm(forms.ModelForm):
    """Formulário unificado: evento de calendário + campos pedagógicos opcionais."""

    class Meta:
        model = AgendaEvento
        fields = [
            # Pedagógicos (em cascata)
            "escola", "turma", "professor", "materia", "livro",
            # Conteúdo do evento
            "titulo", "tipo", "descricao",
            "conteudo", "dever", "observacao",
            # Datas
            "inicio", "termino", "data_entrega",
            # Flags
            "tem_anexo", "enviado_whatsapp",
        ]
        widgets = {
            "escola":    forms.Select(attrs={"class": "form-select shadow-sm", "data-cascade": "escola"}),
            "turma":     forms.Select(attrs={"class": "form-select shadow-sm", "data-cascade": "turma"}),
            "professor": forms.Select(attrs={"class": "form-select shadow-sm", "data-cascade": "professor"}),
            "materia":   forms.Select(attrs={"class": "form-select shadow-sm", "data-cascade": "materia"}),
            "livro":     forms.Select(attrs={"class": "form-select shadow-sm", "data-cascade": "livro"}),
            "titulo": forms.TextInput(
                attrs={"class": "form-control shadow-sm", "placeholder": "Título do evento"}
            ),
            "tipo": forms.TextInput(
                attrs={"class": "form-control shadow-sm", "placeholder": "Ex: Tarefa, Prova, Avaliação"}
            ),
            "descricao": forms.Textarea(
                attrs={"class": "form-control shadow-sm", "rows": 3, "placeholder": "Descrição completa"}
            ),
            "conteudo": forms.Textarea(
                attrs={"class": "form-control shadow-sm", "rows": 2, "placeholder": "Conteúdo ministrado (opcional)"}
            ),
            "dever": forms.Textarea(
                attrs={"class": "form-control shadow-sm", "rows": 2, "placeholder": "Dever de casa (opcional)"}
            ),
            "observacao": forms.Textarea(
                attrs={"class": "form-control shadow-sm", "rows": 2, "placeholder": "Observação geral (opcional)"}
            ),
            "inicio": forms.DateTimeInput(
                attrs={"class": "form-control shadow-sm", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "termino": forms.DateTimeInput(
                attrs={"class": "form-control shadow-sm", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "data_entrega": forms.DateInput(
                attrs={"class": "form-control shadow-sm", "type": "date"},
                format="%Y-%m-%d",
            ),
            "tem_anexo": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "transform: scale(1.3);"}
            ),
            "enviado_whatsapp": forms.CheckboxInput(
                attrs={"class": "form-check-input", "style": "transform: scale(1.3);"}
            ),
        }
        labels = {
            "escola": "Escola", "turma": "Turma", "professor": "Professor",
            "materia": "Matéria", "livro": "Livro",
            "titulo": "Título", "descricao": "Descrição", "tipo": "Tipo",
            "conteudo": "Conteúdo ministrado", "dever": "Dever de casa",
            "observacao": "Observação geral",
            "inicio": "Início", "termino": "Término", "data_entrega": "Data de entrega",
            "tem_anexo": "Possui anexo", "enviado_whatsapp": "Enviado via WhatsApp",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for name in ("escola", "professor", "materia", "livro",
                     "conteudo", "dever", "observacao", "data_entrega",
                     "descricao", "tipo", "tem_anexo", "enviado_whatsapp",
                     "termino"):
            if name in self.fields:
                self.fields[name].required = False
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["termino"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["data_entrega"].input_formats = ["%Y-%m-%d"]

        if user is not None:
            from .services.escopo import aplicar_escopo_no_form
            aplicar_escopo_no_form(self, user)


# ===============================
# 📲 WHATSAPP ENVIO
# ===============================

class WhatsAppEnvioForm(forms.ModelForm):

    class Meta:
        model = WhatsAppEnvio
        fields = ["turma", "hash_evento"]
        widgets = {
            "turma": forms.Select(
                attrs={"class": "form-select shadow-sm border-danger", "style": "border-radius:10px;"}
            ),
            "hash_evento": forms.TextInput(
                attrs={"class": "form-control shadow-sm border-danger", "placeholder": "Hash do evento enviado", "style": "border-radius:10px;"}
            ),
        }
        labels = {"turma": "Turma", "hash_evento": "Hash do Evento"}


# ===============================
# 📚 MATÉRIA
# ===============================

class MateriaForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = ["nome_materia"]
        widgets = {
            "nome_materia": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Matemática"}),
        }


# ===============================
# 👨‍🏫 PROFESSOR
# ===============================

class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ["escola", "materia", "nome_professor"]
        widgets = {
            "escola": forms.Select(attrs={"class": "form-select"}),
            "materia": forms.Select(attrs={"class": "form-select"}),
            "nome_professor": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
        }


# ===============================
# 📖 LIVRO
# ===============================

class LivroForm(forms.ModelForm):
    class Meta:
        model = Livro
        fields = ["escola", "materia", "nome_livro"]
        widgets = {
            "escola": forms.Select(attrs={"class": "form-select"}),
            "materia": forms.Select(attrs={"class": "form-select"}),
            "nome_livro": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome do livro"}),
        }


# ===============================
# 📅 DIA DA SEMANA
# ===============================

class DiasForm(forms.ModelForm):
    class Meta:
        model = Dias
        fields = ["dias", "ordem"]
        widgets = {
            "dias": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Segunda-feira"}),
            "ordem": forms.NumberInput(attrs={"class": "form-control"}),
        }


# ===============================
# 🕐 ORDEM DE HORÁRIO
# ===============================

class OrdemHorarioForm(forms.ModelForm):
    class Meta:
        model = OrdemHorario
        fields = ["ordem", "posicao", "inicio", "termino"]
        widgets = {
            "ordem":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 1ª Aula, Intervalo, Almoço"}),
            "posicao": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Ordem de exibição (menor = primeiro)"}),
            "inicio":  forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "termino": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
        }


# ===============================
# 🗓️ HORÁRIO
# ===============================

class HorarioForm(forms.ModelForm):
    class Meta:
        model = Horario
        fields = ["escola", "turma", "dia", "ordem", "professor", "materia"]
        widgets = {
            "escola":    forms.Select(attrs={"class": "form-select", "data-cascade": "escola"}),
            "turma":     forms.Select(attrs={"class": "form-select", "data-cascade": "turma"}),
            "dia":       forms.Select(attrs={"class": "form-select"}),
            "ordem":     forms.Select(attrs={"class": "form-select"}),
            "professor": forms.Select(attrs={"class": "form-select", "data-cascade": "professor"}),
            "materia":   forms.Select(attrs={"class": "form-select", "data-cascade": "materia"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Professor e matéria são opcionais (intervalo, almoço, lanche, etc.)
        self.fields["professor"].required = False
        self.fields["materia"].required = False
        self.fields["professor"].empty_label = "— (sem professor)"
        self.fields["materia"].empty_label = "— (sem matéria)"
        if user is not None:
            from .services.escopo import aplicar_escopo_no_form
            aplicar_escopo_no_form(self, user)


# ===============================
# 🏫 AULA / DEVER
# ===============================

class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        fields = [
            "escola", "turma", "professor", "materia", "livro",
            "conteudo", "data_aula", "dever", "data_entrega", "observacao",
        ]
        widgets = {
            "escola":       forms.Select(attrs={"class": "form-select"}),
            "turma":        forms.Select(attrs={"class": "form-select"}),
            "professor":    forms.Select(attrs={"class": "form-select"}),
            "materia":      forms.Select(attrs={"class": "form-select"}),
            "livro":        forms.Select(attrs={"class": "form-select"}),
            "conteudo":     forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Conteúdo ministrado..."}),
            "data_aula":    forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "dever":        forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Dever de casa..."}),
            "data_entrega": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observacao":   forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Observações gerais..."}),
        }
        labels = {
            "escola": "Escola", "turma": "Turma", "professor": "Professor",
            "materia": "Matéria", "livro": "Livro", "conteudo": "Conteúdo ministrado",
            "data_aula": "Data da aula", "dever": "Dever de casa",
            "data_entrega": "Data de entrega", "observacao": "Observação geral",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["data_aula"].input_formats = ["%Y-%m-%d"]
        self.fields["data_entrega"].input_formats = ["%Y-%m-%d"]
        # Filtra matéria pelo professor selecionado (POST)
        if "professor" in self.data:
            try:
                prof_id = int(self.data["professor"])
                self.fields["materia"].queryset = Materia.objects.filter(professores__id=prof_id)
            except (ValueError, TypeError):
                pass
        else:
            self.fields["materia"].queryset = Materia.objects.all()

        # Restringe todos os selects à(s) escola(s) do usuário e aplica defaults
        if user is not None:
            from .services.escopo import aplicar_escopo_no_form
            aplicar_escopo_no_form(self, user)


# ===============================
# 📋 DIÁRIO DO ALUNO
# ===============================

class DiarioAlunoForm(forms.ModelForm):
    class Meta:
        model = DiarioAluno
        fields = ["aluno", "presente", "observacao"]
        widgets = {
            "aluno":      forms.HiddenInput(),
            "presente":   forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacao": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Observação individual..."}),
        }
        labels = {"presente": "", "observacao": "Observação"}


DiarioAlunoFormSet = inlineformset_factory(
    Aula, DiarioAluno,
    form=DiarioAlunoForm,
    extra=0,
    can_delete=False,
    fields=["aluno", "presente", "observacao"],
)
