import sys
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .forms import UsuarioForm
from .models import Escola, Turma, ConexaoAgenda


# ---------------------------------------------------------------------------
# Bug 1: sync_agenda — one failing connection must not abort the others
# ---------------------------------------------------------------------------

# sync_agenda imports extrair_eventos from agenda_robot, which imports playwright.
# Stub out playwright at the sys.modules level so the module can be imported in tests.
_playwright_stub = MagicMock()
_playwright_modules = {
    "playwright": _playwright_stub,
    "playwright.sync_api": _playwright_stub,
}


class SyncAgendaIsolationTest(TestCase):
    """
    When one ConexaoAgenda raises during extrair_eventos, the remaining
    connections must still be processed and their results accumulated.
    """

    def setUp(self):
        escola = Escola.objects.create(nome_escola="Escola Teste")
        self.turma_ok   = Turma.objects.create(escola=escola, nome_turma="Turma OK")
        self.turma_fail = Turma.objects.create(escola=escola, nome_turma="Turma Falha")
        ConexaoAgenda.objects.create(turma=self.turma_fail, login="u1", senha="p1", ativo=True)
        ConexaoAgenda.objects.create(turma=self.turma_ok,   login="u2", senha="p2", ativo=True)

    def _failing_first_side_effect(self):
        def side_effect(login, senha):
            if login == "u1":
                raise RuntimeError("Falha simulada de conexao")
            return [{"titulo": "Evento", "data": "2025-01-01", "dia": "Qua",
                     "tipo": "Atividade", "datas": "2025-01-01", "descricao": "Desc"}]
        return side_effect

    def _import_sync(self):
        """Import sync_agenda with playwright stubbed out."""
        with patch.dict(sys.modules, _playwright_modules):
            import importlib
            import agenda.services.sync_agenda as mod
            importlib.reload(mod)
            return mod

    def test_continues_after_one_failure(self):
        """sincronizar_agenda() must process all connections even when one fails."""
        mod = self._import_sync()
        with patch.object(mod, "extrair_eventos", side_effect=self._failing_first_side_effect()), \
             patch.object(mod, "salvar_eventos", return_value={"salvos": 1, "ignorados": 0}) as mock_salvar:
            mod.sincronizar_agenda()  # must not raise
            self.assertEqual(mock_salvar.call_count, 1)

    def test_com_resultado_counts_errors(self):
        """sincronizar_agenda_com_resultado() must count errors and still return totals."""
        mod = self._import_sync()
        with patch.object(mod, "extrair_eventos", side_effect=self._failing_first_side_effect()), \
             patch.object(mod, "salvar_eventos", return_value={"salvos": 2, "ignorados": 1}):
            result = mod.sincronizar_agenda_com_resultado()

        self.assertEqual(result["erros"], 1)
        self.assertEqual(result["conexoes"], 1)
        self.assertEqual(result["salvos"], 2)
        self.assertEqual(result["ignorados"], 1)

    def test_com_resultado_all_fail_no_exception(self):
        """When all connections fail, result has erros=2 and salvos=0 — no exception raised."""
        mod = self._import_sync()
        with patch.object(mod, "extrair_eventos", side_effect=RuntimeError("Falha total")), \
             patch.object(mod, "salvar_eventos") as mock_salvar:
            result = mod.sincronizar_agenda_com_resultado()

        self.assertEqual(result["erros"], 2)
        self.assertEqual(result["salvos"], 0)
        mock_salvar.assert_not_called()


# ---------------------------------------------------------------------------
# Bug 2: desativar_usuario — must reject GET requests
# ---------------------------------------------------------------------------

class DesativarUsuarioCSRFTest(TestCase):
    """
    desativar_usuario must only accept POST. A GET request must not
    deactivate the account.
    """

    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin", password="adminpass", is_staff=True, is_superuser=True
        )
        self.target = User.objects.create_user(
            username="alvo", password="alvopass", is_active=True
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass")

    def test_get_does_not_deactivate(self):
        """GET to desativar_usuario must not change is_active."""
        url = reverse("cal:desativar_usuario", args=[self.target.id])
        self.client.get(url)

        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_post_deactivates_user(self):
        """POST to desativar_usuario must set is_active=False."""
        url = reverse("cal:desativar_usuario", args=[self.target.id])
        response = self.client.post(url)

        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertRedirects(response, reverse("cal:listar_usuarios"))


# ---------------------------------------------------------------------------
# Bug 3: UsuarioForm — must hash the password and reject mismatched passwords
# ---------------------------------------------------------------------------

class UsuarioFormPasswordTest(TestCase):
    """
    UsuarioForm must require a password, validate confirmation, and save
    the account with a properly hashed (usable) password.
    """

    def _valid_data(self, password="Senha@123", confirm=None):
        return {
            "username": "novousuario",
            "email": "novo@exemplo.com",
            "first_name": "",
            "last_name": "",
            "is_staff": False,
            "password": password,
            "confirmar_senha": confirm if confirm is not None else password,
        }

    def test_valid_form_creates_usable_password(self):
        """Saved user must have a usable (hashed) password."""
        form = UsuarioForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("Senha@123"))

    def test_mismatched_passwords_invalid(self):
        """Form must be invalid when passwords do not match."""
        form = UsuarioForm(data=self._valid_data(password="abc", confirm="xyz"))
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_missing_password_invalid(self):
        """Form must be invalid when password field is empty."""
        data = self._valid_data()
        data["password"] = ""
        data["confirmar_senha"] = ""
        form = UsuarioForm(data=data)
        self.assertFalse(form.is_valid())

    def test_view_creates_usable_account(self):
        """The adicionar_usuario view must produce a user with a usable password."""
        User.objects.create_user(
            username="admin", password="adminpass", is_staff=True, is_superuser=True
        )
        client = Client()
        client.login(username="admin", password="adminpass")

        response = client.post(reverse("cal:adicionar_usuario"), {
            "username": "pairesponsavel",
            "email": "pai@escola.com",
            "first_name": "",
            "last_name": "",
            "is_staff": False,
            "password": "Senha@456",
            "confirmar_senha": "Senha@456",
        })

        self.assertRedirects(response, reverse("cal:listar_usuarios"))
        user = User.objects.get(username="pairesponsavel")
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("Senha@456"))


# ---------------------------------------------------------------------------
# fechar_tutorial — must swallow only PlaywrightTimeoutError, not all errors
# ---------------------------------------------------------------------------

class FecharTutorialTest(TestCase):
    """
    fechar_tutorial() must silently skip when the modal is absent (TimeoutError),
    but must not suppress unrelated Playwright errors.
    """

    def _import_robot(self):
        """Import agenda_robot with playwright stubbed out."""
        import importlib
        with patch.dict(sys.modules, _playwright_modules):
            import agenda.agenda_robot as mod
            importlib.reload(mod)
            return mod

    def test_timeout_is_silently_ignored(self):
        """A PlaywrightTimeoutError from wait_for must not propagate."""
        mod = self._import_robot()

        # Inject the real PlaywrightTimeoutError class so the except clause matches.
        real_timeout = type("TimeoutError", (Exception,), {})
        mod.PlaywrightTimeoutError = real_timeout

        page = MagicMock()
        modal = MagicMock()
        page.locator.return_value = modal
        modal.wait_for.side_effect = real_timeout("timed out")

        # Must not raise.
        mod.fechar_tutorial(page)

    def test_non_timeout_exception_propagates(self):
        """Errors other than TimeoutError must not be swallowed."""
        mod = self._import_robot()

        real_timeout = type("TimeoutError", (Exception,), {})
        mod.PlaywrightTimeoutError = real_timeout

        page = MagicMock()
        modal = MagicMock()
        page.locator.return_value = modal
        # Simulate an unexpected error (e.g. browser crash), not a timeout.
        modal.wait_for.side_effect = RuntimeError("browser disconnected")

        with self.assertRaises(RuntimeError):
            mod.fechar_tutorial(page)
