import os
import json
import logging
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

COOKIES_PATH = "agenda/storage/cookies.json"

# Mirrors the headers observed in Burp Suite captures.
API_HEADERS = {
    "Accept": "application/json",
    "Plataforma": "2",
    "Front-Version": "4.25.50",
    "Origin": "https://mb4.bernoulli.com.br",
    "Referer": "https://mb4.bernoulli.com.br/",
}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Modal helpers
# ---------------------------------------------------------------------------

def fechar_boasvindas(page):
    """
    Dismisses the 'Que bom ter você aqui' welcome modal when present.
    Silently skips on timeout (modal absent or already dismissed).
    """
    try:
        overlay = page.locator("div").filter(has_text="Que bom ter você aqui").nth(1)
        overlay.wait_for(state="visible", timeout=4000)

        # The close/advance button is the third button on the page at that point.
        page.get_by_role("button").nth(2).click()

        overlay.wait_for(state="hidden", timeout=4000)
        logger.info("Modal de boas-vindas fechado")
    except PlaywrightTimeoutError:
        pass


def fechar_tutorial(page):
    """
    Closes the Bernoulli tutorial modal if visible.

    Silently skips when the modal is absent (PlaywrightTimeoutError). Any other
    exception (e.g. browser disconnected) is allowed to propagate so callers are
    not left unaware of real failures.
    """
    try:
        modal = page.locator(".TutorialInitial")
        modal.wait_for(state="visible", timeout=4000)

        btn_fechar = page.locator('[tooltip="Desabilitar tutorial"] button')
        btn_fechar.click()

        modal.wait_for(state="hidden", timeout=4000)
        logger.info("Modal de tutorial fechado")
    except PlaywrightTimeoutError:
        # Modal not present — nothing to close.
        pass


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def extrair_token(page):
    """
    Reads the JWT Bearer token from localStorage after a successful login.

    The Bernoulli SPA stores the token under several possible keys. Returns
    the token string, or None if not found.
    """
    token = page.evaluate("""
        () => {
            const candidates = Object.keys(localStorage).filter(k =>
                k.toLowerCase().includes('token') ||
                k.toLowerCase().includes('auth') ||
                k.toLowerCase().includes('jwt')
            );
            for (const key of candidates) {
                const val = localStorage.getItem(key);
                if (val && val.startsWith('eyJ')) return val;
                try {
                    const obj = JSON.parse(val);
                    const t = obj.token || obj.access_token || obj.accessToken;
                    if (t && t.startsWith('eyJ')) return t;
                } catch (_) {}
            }
            return null;
        }
    """)

    if token:
        logger.info("Token JWT extraído do localStorage")
    else:
        logger.warning("Token JWT não encontrado no localStorage — fetch usará contexto de sessão")

    return token


# ---------------------------------------------------------------------------
# Date window
# ---------------------------------------------------------------------------

def janela_datas():
    """
    Returns (data_inicio, data_fim) covering the current month through the
    end of the following month.
    """
    hoje = datetime.now()
    inicio = hoje.replace(day=1)
    primeiro_proximo = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
    ultimo_proximo = (primeiro_proximo + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return inicio.strftime("%Y-%m-%d"), ultimo_proximo.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extrair_eventos(login, senha):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=USER_AGENT)

        if os.path.exists(COOKIES_PATH):
            try:
                with open(COOKIES_PATH, "r") as f:
                    context.add_cookies(json.load(f))
                logger.info("Cookies carregados")
            except Exception:
                pass

        page = context.new_page()

        try:
            logger.info("Acessando sistema...")
            page.goto(
                "https://mb4.bernoulli.com.br/minhaarea",
                wait_until="load",
                timeout=60000,
            )

            needs_login = (
                "login" in page.url
                or page.get_by_role("textbox", name="Login").is_visible(timeout=5000)
            )

            if needs_login:
                logger.info("Fazendo login...")
                page.goto("https://mb4.bernoulli.com.br/login")
                page.get_by_role("textbox", name="Login").fill(login)
                page.get_by_role("textbox", name="Senha").fill(senha)
                page.get_by_role("button", name="ENTRAR").click()

                try:
                    page.get_by_role("button", name="AVANÇAR").click(timeout=10000)
                except PlaywrightTimeoutError:
                    pass

                # page.wait_for_url("**/minhaarea**", timeout=20000)
                print("needs_login")
                page.get_by_role("button", name="Minha Área").click()
                page.get_by_role("button", name="Agenda").click()

                fechar_boasvindas(page)
                fechar_tutorial(page)

                with open(COOKIES_PATH, "w") as f:
                    json.dump(context.cookies(), f)
                logger.info("Cookies salvos")
            else:
                print("needs_login else")
                fechar_boasvindas(page)
                fechar_tutorial(page)

            # Wait for the SPA to finish loading the auth token into localStorage.
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Minha Área").click()
            page.get_by_role("button", name="Agenda").click()
            token = extrair_token(page)

            data_inicio, data_fim = janela_datas()
            url_api = (
                
                f"https://api.bernoulli.com.br/api/comunicacao/agenda/listar"
                f"?dataInicio={data_inicio}&dataTermino={data_fim}"
            )
            logger.info(f"Consultando API: {data_inicio} até {data_fim}")

            headers_js = dict(API_HEADERS)
            if token:
                headers_js["Authorization"] = f"Bearer {token}"

            script = f"""
                async () => {{
                    const resp = await fetch("{url_api}", {{
                        headers: {json.dumps(headers_js)}
                    }});
                    return await resp.json();
                }}
            """

            resultado = page.evaluate(script)
            eventos = resultado.get("data", [])
            logger.info(f"{len(eventos)} eventos encontrados")

            eventos_formatados = []
            for item in eventos:
                eventos_formatados.append({
                    "data": item.get("dataInicio", "").split("T")[0],
                    "dia": "",
                    "titulo": item.get("titulo", "Sem título"),
                    "tipo": item.get("tipoAgenda", {}).get("descricao", ""),
                    "datas": f"{item.get('dataInicio')} - {item.get('dataFim')}",
                    "descricao": item.get("descricao", ""),
                })

            return eventos_formatados

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout: {e}")
            return []

        except Exception as e:
            logger.error(f"Erro: {e}")
            return []

        finally:
            browser.close()
