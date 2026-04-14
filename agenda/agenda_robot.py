import os
import json
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

COOKIES_PATH = "agenda/storage/cookies.json"


def extrair_eventos(login, senha):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # -------------------------------
        # COOKIES
        # -------------------------------
        if os.path.exists(COOKIES_PATH):
            try:
                with open(COOKIES_PATH, "r") as f:
                    context.add_cookies(json.load(f))
                logger.info("🍪 Cookies carregados")
            except:
                pass

        page = context.new_page()

        try:
            logger.info("🔗 Acessando sistema...")
            page.goto(
                "https://mb4.bernoulli.com.br/minhaarea",
                wait_until="load",
                timeout=60000
            )

            # -------------------------------
            # LOGIN (SE NECESSÁRIO)
            # -------------------------------
            if (
                    "login" in page.url or
                    page.get_by_role("textbox", name="Login").is_visible(timeout=5000)
                ):
            
            
                logger.info("🔑 Fazendo login...")

                page.goto("https://mb4.bernoulli.com.br/login")

                page.get_by_role("textbox", name="Login").fill(login)
                page.get_by_role("textbox", name="Senha").fill(senha)

                page.get_by_role("button", name="ENTRAR").click()

                try:
                    page.get_by_role("button", name="AVANÇAR").click(timeout=10000)
                except:
                    pass

                page.wait_for_url("**/minhaarea**", timeout=20000)

                # salva cookies
                with open(COOKIES_PATH, "w") as f:
                    json.dump(context.cookies(), f)

            # 🔥 IMPORTANTE: aguarda token carregar
            page.wait_for_timeout(3000)

            # -------------------------------
            # API (AJUSTE DE DATAS DINÂMICO)
            # -------------------------------
            from datetime import datetime, timedelta

            hoje = datetime.now()
            inicio = hoje - timedelta(days=7)
            fim = hoje + timedelta(days=7)

            data_inicio = inicio.strftime("%Y-%m-%d")
            data_fim = fim.strftime("%Y-%m-%d")

            url_api = f"https://api.bernoulli.com.br/api/comunicacao/agenda/listar?dataInicio={data_inicio}&dataTermino={data_fim}"

            logger.info(f"📡 Consultando API: {data_inicio} até {data_fim}")

            script = f"""
                async () => {{
                    const resp = await fetch("{url_api}", {{
                        headers: {{
                            "Accept": "application/json",
                            "Plataforma": "2",
                            "Front-Version": "4.25.50"
                        }}
                    }});
                    return await resp.json();
                }}
            """

            resultado = page.evaluate(script)

            eventos = resultado.get("data", [])

            logger.info(f"📊 {len(eventos)} eventos encontrados")

            # -------------------------------
            # FORMATAÇÃO PARA DJANGO
            # -------------------------------
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
            logger.error(f"❌ Timeout: {e}")
            return []

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            return []

        finally:
            browser.close()