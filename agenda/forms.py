from django import forms
from django.contrib.auth.models import User
from .models import (
    Escola,
    Turma,
    Aluno,
    ConexaoAgenda,
    AgendaEvento,
    WhatsAppEnvio,
    TarefaCompleta,
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
        fields = ["turma", "nome_aluno", "usuarios"]
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
        }
        labels = {
            "turma": "Turma",
            "nome_aluno": "Nome do Aluno",
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

    class Meta:
        model = AgendaEvento
        fields = ["turma", "data", "dia", "titulo", "tipo", "datas", "descricao"]
        widgets = {
            "turma": forms.Select(
                attrs={"class": "form-select shadow-sm border-dark", "style": "border-radius:10px;"}
            ),
            "data": forms.DateInput(
                attrs={"class": "form-control shadow-sm border-dark", "type": "date", "style": "border-radius:10px;"}
            ),
            "dia": forms.TextInput(
                attrs={"class": "form-control shadow-sm border-dark", "placeholder": "Ex: Seg", "style": "border-radius:10px;"}
            ),
            "titulo": forms.TextInput(
                attrs={"class": "form-control shadow-sm border-dark", "placeholder": "Título do evento", "style": "border-radius:10px;"}
            ),
            "tipo": forms.TextInput(
                attrs={"class": "form-control shadow-sm border-dark", "placeholder": "Ex: Atividade, Prova, Lição", "style": "border-radius:10px;"}
            ),
            "datas": forms.TextInput(
                attrs={"class": "form-control shadow-sm border-dark", "placeholder": "Datas relacionadas", "style": "border-radius:10px;"}
            ),
            "descricao": forms.Textarea(
                attrs={"class": "form-control shadow-sm border-dark", "rows": 4, "placeholder": "Descrição completa", "style": "border-radius:10px;"}
            ),
        }
        labels = {
            "turma": "Turma", "data": "Data", "dia": "Dia",
            "titulo": "Título", "tipo": "Tipo", "datas": "Datas", "descricao": "Descrição"
        }


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
