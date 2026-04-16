import os
import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BRASILIA = ZoneInfo("America/Sao_Paulo")


class _TextExtractor(HTMLParser):
    """Converts HTML to plain text, preserving URLs as bare text."""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        if tag in ("br", "p", "div", "li"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        text = "".join(self._parts)
        # Replace non-breaking spaces with regular spaces
        text = text.replace("\xa0", " ")
        # Remove lines that are only whitespace
        lines = [ln.strip() for ln in text.splitlines()]
        # Drop consecutive empty lines (keep at most one blank line between paragraphs)
        result = []
        prev_blank = False
        for ln in lines:
            if ln == "":
                if not prev_blank:
                    result.append("")
                prev_blank = True
            else:
                result.append(ln)
                prev_blank = False
        return "\n".join(result).strip()


def html_para_texto(html):
    """
    Strips HTML tags and returns clean plain text.
    URLs that were inside <a href> tags are preserved as bare text
    because handle_data already captures the link text or the URL itself.
    """
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()

logger = logging.getLogger(__name__)

COOKIES_PATH = "agenda/storage/cookies.json"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def formatar_data_bernoulli(data_str):
    """
    Converts Bernoulli date strings to timezone-aware datetime objects.

    Handles two formats produced by the Lista view:
      - 'ter., 10/03/26, 10:50'  → datetime(2026, 3, 10, 10, 50, tzinfo=America/Sao_Paulo)
      - '10/03/26, 10:50'        → datetime(2026, 3, 10, 10, 50, tzinfo=America/Sao_Paulo)

    Returns None on parse failure so callers can decide how to handle it.
    """
    if not data_str:
        return None
    try:
        partes = [p.strip() for p in data_str.split(',')]
        # Drop the weekday prefix when present (e.g. 'ter.')
        if len(partes) == 3:
            partes = partes[1:]
        data_limpa = f"{partes[0].strip()} {partes[1].strip()}"
        naive = datetime.strptime(data_limpa, "%d/%m/%y %H:%M")
        # Bernoulli displays times in Brasília time (BRT/BRST).
        return naive.replace(tzinfo=BRASILIA)
    except Exception as e:
        logger.warning(f"Não foi possível converter data '{data_str}': {e}")
        return None


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
# Download URL capture
# ---------------------------------------------------------------------------

def _capturar_url_download(page, btn_locator):
    """
    Clicks the download button and intercepts the resulting network request
    to extract the file URL without saving the file to disk.

    The Bernoulli download button triggers a JS-driven request (no static href).
    We use Playwright's expect_download() context manager to catch the download
    event and read the URL from the response.

    Returns the URL string, or "" if interception fails or times out.
    """
    try:
        # expect_download() catches the browser's download event triggered by
        # the button click, giving us access to the resolved URL.
        with page.expect_download(timeout=10000) as download_info:
            # The icon <i> is not clickable — find the parent <button>
            clickable = btn_locator
            tag = btn_locator.evaluate("el => el.tagName.toLowerCase()")
            if tag != "button":
                clickable = btn_locator.locator("xpath=ancestor::button[1]")
                if clickable.count() == 0:
                    clickable = btn_locator.locator("xpath=ancestor-or-self::*[@role='button'][1]")
            clickable.click()

        download = download_info.value
        url = download.url
        logger.info(f"URL de download capturada: {url}")
        return url
    except PlaywrightTimeoutError:
        logger.warning("Timeout ao tentar capturar URL de download — sem anexo acessível")
        return ""
    except Exception as e:
        logger.warning(f"Erro ao capturar URL de download: {e}")
        return ""


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extrair_eventos(login, senha):
    """
    Logs into Bernoulli, switches to the Lista view, and scrapes the event
    table. Returns a list of dicts ready to be passed to salvar_eventos().
    """
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
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
            logger.info("Acessando agenda...")
            page.goto(
                "https://mb4.bernoulli.com.br/minhaarea/agenda",
                wait_until="load",
                timeout=60000,
            )

            # ------------------------------------------------------------------
            # Login when session cookie is expired or absent
            # ------------------------------------------------------------------
            if "login" in page.url or page.get_by_role("textbox", name="Login").is_visible(timeout=5000):
                logger.info("Fazendo login...")
                page.goto("https://mb4.bernoulli.com.br/login")
                page.get_by_role("textbox", name="Login").fill(login)
                page.get_by_role("textbox", name="Senha").fill(senha)
                page.get_by_role("button", name="ENTRAR").click()

                try:
                    page.get_by_role("button", name="AVANÇAR").click(timeout=10000)
                except PlaywrightTimeoutError:
                    pass

                page.wait_for_url("**/minhaarea**", timeout=20000)

                fechar_boasvindas(page)
                fechar_tutorial(page)

                # Navigate to agenda after login
                page.goto(
                    "https://mb4.bernoulli.com.br/minhaarea/agenda",
                    wait_until="load",
                    timeout=30000,
                )

                with open(COOKIES_PATH, "w") as f:
                    json.dump(context.cookies(), f)
                logger.info("Cookies salvos")
            else:
                fechar_boasvindas(page)
                fechar_tutorial(page)

            # ------------------------------------------------------------------
            # Switch to Lista view and wait for the table
            # ------------------------------------------------------------------
            logger.info("Alternando para visão Minha Área...")
            page.get_by_role("button", name="Minha Área").click()
            logger.info("Alternando para visão Agenda...")
            page.get_by_role("button", name="Agenda").click()
            logger.info("Alternando para visão Lista...")
            page.get_by_role("button", name="Lista").click()
            page.wait_for_selector("table tbody tr", timeout=15000)

            # ------------------------------------------------------------------
            # Scrape the table
            # ------------------------------------------------------------------
            linhas = page.locator("table tbody tr").all()
            logger.info(f"{len(linhas)} linhas encontradas na tabela")

            eventos_coletados = []

            for linha in linhas:
                colunas = linha.locator("td").all()
                if len(colunas) < 5:
                    continue

                titulo = colunas[0].inner_text().strip()
                # Convert HTML description to plain text; URLs are kept as bare text.
                descricao = html_para_texto(colunas[1].inner_html())
                inicio_raw = colunas[2].inner_text().strip()
                termino_raw = colunas[3].inner_text().strip()
                tipo = colunas[4].locator("span").first.inner_text().strip()

                # Column 5 (Ações) — detect download button and capture URL
                tem_anexo = False
                url_anexo = ""
                if len(colunas) >= 6:
                    btn_download = colunas[5].locator(
                        "button[tooltip*='Baixar'], button[tooltip*='baixar'], "
                        "button[tooltip*='download'], button[tooltip*='Download'], "
                        "i.ph-file-arrow-down, [class*='file-arrow-down']"
                    ).first
                    if btn_download.count() > 0:
                        tem_anexo = True
                        url_anexo = _capturar_url_download(page, btn_download)

                inicio = formatar_data_bernoulli(inicio_raw)
                termino = formatar_data_bernoulli(termino_raw)

                eventos_coletados.append({
                    # New structured fields
                    "inicio": inicio,
                    "termino": termino,
                    "tem_anexo": tem_anexo,
                    "url_anexo": url_anexo,
                    # Core fields
                    "titulo": titulo,
                    "descricao": descricao,
                    "tipo": tipo,
                    # Legacy fields kept for hash compatibility and fallback display
                    "data": inicio.date() if inicio else None,
                    "dia": "",
                    "datas": f"{inicio_raw} — {termino_raw}",
                })

            logger.info(f"{len(eventos_coletados)} eventos extraídos")
            return eventos_coletados

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout: {e}")
            return []

        except Exception as e:
            logger.error(f"Erro: {e}")
            return []

        finally:
            browser.close()
