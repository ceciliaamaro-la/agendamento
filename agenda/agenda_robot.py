from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import re
import logging
import os
import json
import time
import random

logger = logging.getLogger(__name__)

COOKIES_PATH = "agenda/storage/cookies.json"


# -------------------------------
# COOKIES
# -------------------------------

def carregar_cookies(context):

    if os.path.exists(COOKIES_PATH):

        try:

            with open(COOKIES_PATH, "r") as f:
                cookies = json.load(f)

            context.add_cookies(cookies)

            logger.info("🍪 Cookies carregados")

            return True

        except Exception as e:

            logger.warning("⚠️ Cookies inválidos. Recriando.")

            os.remove(COOKIES_PATH)

            return False

    return False


def salvar_cookies(context):

    logger.info("💾 Salvando cookies")

    cookies = context.cookies()

    with open(COOKIES_PATH, "w") as f:

        json.dump(cookies, f)


# -------------------------------
# DELAY HUMANO (anti-bloqueio)
# -------------------------------

def delay():

    time.sleep(random.uniform(1.2, 2.6))


# -------------------------------
# ROBO
# -------------------------------

def extrair_eventos(login, senha):

    logger.info("🤖 Iniciando robô")

    dados = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context()

        page = context.new_page()

        # -------------------------------
        # LOGIN COM COOKIES
        # -------------------------------

        logado = carregar_cookies(context)

        if logado:

            logger.info("⚡ Login via cookies")

            page.goto("https://mb4.bernoulli.com.br/minhaarea")

        else:

            logger.info("🔐 Fazendo login")

            page.goto("https://mb4.bernoulli.com.br/login")

            page.get_by_role("textbox", name="Login").fill(login)
            page.get_by_role("textbox", name="Senha").fill(senha)

            delay()

            page.get_by_role("button", name="ENTRAR").click()

            page.wait_for_load_state("networkidle")

            salvar_cookies(context)

        delay()

        # -------------------------------
        # IR PARA AGENDA
        # -------------------------------

        page.goto("https://mb4.bernoulli.com.br/minhaarea/agenda")

        page.wait_for_selector(".calendario-table-days")

        logger.info("📅 Lendo agenda")

        semanas = page.query_selector_all(".calendario-table-days .semana")

        hoje = datetime.now().date()
        limite = hoje + timedelta(days=3)

        for semana in semanas:

            dias = semana.query_selector_all(".semana-day")

            for dia in dias:

                data_iso = dia.get_attribute("data-date")

                if not data_iso:
                    continue

                data = datetime.fromisoformat(data_iso.replace("Z", ""))

                if not (hoje <= data.date() <= limite):
                    continue

                numero_dia = dia.query_selector(".day").inner_text()

                eventos = dia.query_selector_all(".tag-circle")

                if not eventos:
                    continue

                page.locator("a").filter(has_text=numero_dia).first.click()

                page.wait_for_selector(".EventItem")

                lista_eventos = page.locator(".EventItem")

                total = lista_eventos.count()

                for i in range(total):

                    evento = lista_eventos.nth(i)

                    evento.click()

                    modal = page.locator(".ModalContent.Event")

                    modal.wait_for()

                    titulo = modal.locator(".title-24-600").inner_text()

                    tipo = modal.locator(".Tag span").inner_text()

                    datas = modal.locator(".ph-calendar").locator("xpath=..").inner_text()

                    descricao = modal.locator(".event-description").inner_text()

                    arquivos = []

                    downloads = modal.locator(".FileDownload")

                    qtd = downloads.count()

                    for j in range(qtd):

                        item = downloads.nth(j)

                        nome_arquivo = item.inner_text()

                        link = item.locator("a").get_attribute("href")

                        arquivos.append({
                            "nome": nome_arquivo,
                            "link": link
                        })

                    dados.append({

                        "data": data.date(),
                        "dia": numero_dia,
                        "titulo": titulo,
                        "tipo": tipo,
                        "datas": datas,
                        "descricao": descricao,
                        "arquivos": arquivos

                    })

                    logger.info(f"📌 Evento capturado: {titulo}")

                    # fechar modal
                    page.keyboard.press("Escape")

                    delay()

        browser.close()

    logger.info(f"📊 Total eventos coletados: {len(dados)}")

    return dados