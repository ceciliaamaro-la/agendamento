from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timedelta
import logging
import os
import json
import time
import random
import traceback

logger = logging.getLogger(__name__)

COOKIES_PATH = "agenda/storage/cookies.json"


# -------------------------------
# FECHAR MODAL TUTORIAL
# -------------------------------

def fechar_tutorial(page):
    """
    Fecha o modal de tutorial do Bernoulli, caso esteja visível.
    O botão de fechar tem o atributo tooltip="Desabilitar tutorial".
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


# -------------------------------
# COOKIES
# -------------------------------

def carregar_cookies(context):
    """
    Carrega cookies salvos para evitar login manual.
    Retorna True se conseguiu carregar, False caso contrário.
    """
    if not os.path.exists(COOKIES_PATH):
        return False

    try:
        with open(COOKIES_PATH, "r") as f:
            conteudo = f.read().strip()

        if not conteudo:
            logger.warning("Arquivo de cookies vazio. Ignorando.")  # ALTERADO: removido ⚠️
            os.remove(COOKIES_PATH)
            return False

        cookies = json.loads(conteudo)

        if not isinstance(cookies, list) or len(cookies) == 0:
            logger.warning("Cookies inválidos. Ignorando.")  # ALTERADO: removido ⚠️
            os.remove(COOKIES_PATH)
            return False

        context.add_cookies(cookies)
        logger.info("Cookies carregados com sucesso")  # ALTERADO: removido 🍪
        return True

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Erro ao carregar cookies: {e}. Recriando.")  # ALTERADO: removido ⚠️
        if os.path.exists(COOKIES_PATH):
            os.remove(COOKIES_PATH)
        return False


def salvar_cookies(context):
    """
    Salva cookies após login bem-sucedido para uso futuro.
    """
    os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)

    cookies = context.cookies()

    with open(COOKIES_PATH, "w") as f:
        json.dump(cookies, f)

    logger.info("Cookies salvos")  # ALTERADO: removido 💾


# -------------------------------
# DELAY HUMANO (anti-bloqueio)
# -------------------------------

def delay():
    """Pausa aleatória para simular comportamento humano e evitar bloqueios."""
    time.sleep(random.uniform(1.2, 2.6))


# -------------------------------
# EXTRAIR EVENTOS DO MODAL
# -------------------------------

def extrair_dados_do_modal(page, data, numero_dia):
    """
    Extrai todos os dados de um evento a partir do modal aberto.
    Retorna um dicionário com as informações do evento.
    """
    modal = page.locator(".ModalContent.Event")
    modal.wait_for(timeout=10000)

    titulo = modal.locator(".title-24-600").inner_text()
    tipo = modal.locator(".Tag span").inner_text()
    datas = modal.locator(".ph-calendar").locator("xpath=..").inner_text()
    descricao = modal.locator(".event-description").inner_text()

    # Extrair arquivos anexados
    arquivos = []
    downloads = modal.locator(".FileDownload")
    qtd = downloads.count()

    for j in range(qtd):
        item = downloads.nth(j)
        nome_arquivo = item.inner_text()
        link = item.locator("a").get_attribute("href")
        arquivos.append({"nome": nome_arquivo, "link": link})

    return {
        "data": data.date(),
        "dia": numero_dia,
        "titulo": titulo,
        "tipo": tipo,
        "datas": datas,
        "descricao": descricao,
        "arquivos": arquivos
    }


# -------------------------------
# ROBO PRINCIPAL
# -------------------------------

def extrair_eventos(login, senha):
    """
    Função principal que automatiza a extração de eventos da agenda do Bernoulli.
    
    Melhorias implementadas:
    1. ✅ Removido wait_for_load_state("networkidle") que causava timeout
    2. ✅ Adicionado tratamento robusto de erros com try/except em cada etapa
    3. ✅ Extração de dados modularizada em função separada
    4. ✅ Timeouts configuráveis e aumentados para elementos críticos
    5. ✅ Logs mais detalhados para facilitar debug
    6. ✅ Verificação de elementos antes de interagir
    7. ✅ Graceful degradation (continua mesmo se um evento falhar)
    """
    logger.info("Iniciando robo")  # ALTERADO: removido 🤖

    dados = []

    try:
        with sync_playwright() as p:
            # Configuração do browser com opções anti-detecção
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Configurar timeout global (aumentado para evitar timeouts prematuros)
            page.set_default_timeout(45000)  # 45 segundos

            # ----------------------------
            # LOGIN COM COOKIES
            # ----------------------------
            logado = carregar_cookies(context)

            if logado:
                logger.info("Login via cookies")  # ALTERADO: removido ⚡
                page.goto("https://mb4.bernoulli.com.br/minhaarea", wait_until="domcontentloaded")
            else:
                logger.info("Fazendo login com usuario e senha")  # ALTERADO: removido 🔐
                page.goto("https://mb4.bernoulli.com.br/login", wait_until="domcontentloaded")

                # Preencher credenciais
                page.get_by_role("textbox", name="Login").fill(login)
                page.get_by_role("textbox", name="Senha").fill(senha)

                delay()
                page.get_by_role("button", name="ENTRAR").click()
                page.get_by_role("button", name="AVANCAR").click()
                
                # Aguardar navegação pós-login
                # page.wait_for_url("**/minhaarea**", timeout=30000)
                page.goto("https://mb4.bernoulli.com.br/minhaarea", wait_until="domcontentloaded")
                
                fechar_tutorial(page)
                salvar_cookies(context)

            delay()
            fechar_tutorial(page)

            # ----------------------------
            # IR PARA AGENDA
            # ----------------------------
            logger.info("Navegando para agenda...")  # ALTERADO: removido 📅
            
            # Usando wait_until="domcontentloaded" em vez de "networkidle" para evitar timeout
            page.goto(
                "https://mb4.bernoulli.com.br/minhaarea/agenda", 
                wait_until="domcontentloaded"
            )
            
            # Fechar tutorial novamente (pode aparecer em diferentes momentos)
            fechar_tutorial(page)
            
            # Aguardar o calendário carregar (elemento crítico)
            logger.info("Aguardando carregamento do calendario...")  # ALTERADO: removido ⏳
            page.wait_for_selector(".calendario-table-days", state="visible", timeout=30000)
            
            logger.info("Calendario carregado, iniciando leitura de eventos")  # ALTERADO: removido 📅

            # ----------------------------
            # EXTRAIR EVENTOS
            # ----------------------------
            semanas = page.query_selector_all(".calendario-table-days .semana")

            hoje = datetime.now().date()
            limite = hoje + timedelta(days=6)

            for semana_idx, semana in enumerate(semanas):
                logger.debug(f"Processando semana {semana_idx + 1}")
                
                dias = semana.query_selector_all(".semana-day")

                for dia in dias:
                    try:
                        data_iso = dia.get_attribute("data-date")

                        if not data_iso:
                            continue

                        data = datetime.fromisoformat(data_iso.replace("Z", ""))

                        # Filtrar apenas datas no intervalo desejado
                        if not (hoje <= data.date() <= limite):
                            continue

                        day_el = dia.query_selector(".day")

                        if not day_el:
                            continue

                        numero_dia = day_el.inner_text()

                        eventos = dia.query_selector_all(".tag-circle")

                        if not eventos:
                            continue

                        # Clicar no dia que tem eventos
                        logger.info(f"Dia {numero_dia}/{data.month} tem {len(eventos)} evento(s)")  # ALTERADO: removido 📆
                        
                        page.locator("a").filter(has_text=numero_dia).first.click()
                        
                        # Aguardar lista de eventos carregar
                        page.wait_for_selector(".EventItem", state="visible", timeout=15000)

                        lista_eventos = page.locator(".EventItem")
                        total = lista_eventos.count()

                        for i in range(total):
                            try:
                                # Clicar no evento para abrir modal
                                evento = lista_eventos.nth(i)
                                evento.click()

                                # Extrair dados do modal
                                evento_dados = extrair_dados_do_modal(page, data, numero_dia)
                                dados.append(evento_dados)

                                logger.info(f"Evento capturado: {evento_dados['titulo'][:50]}...")  # ALTERADO: removido 📌

                                # Fechar modal
                                page.keyboard.press("Escape")
                                delay()  # Pequena pausa entre eventos

                            except Exception as e:
                                logger.error(f"Erro ao processar evento {i + 1} do dia {numero_dia}: {e}")  # ALTERADO: removido ❌
                                # Tentar fechar modal se estiver preso
                                try:
                                    page.keyboard.press("Escape")
                                except:
                                    pass
                                continue

                    except Exception as e:
                        logger.error(f"Erro ao processar dia: {e}")  # ALTERADO: removido ❌
                        continue

            browser.close()
            logger.info("Navegador fechado")  # ALTERADO: removido ✅

    except Exception as e:
        logger.error(f"Erro critico no robo: {e}")  # ALTERADO: removido ❌
        traceback.print_exc()

    logger.info(f"Total eventos coletados: {len(dados)}")  # ALTERADO: removido 📊
    return dados


# -------------------------------
# EXECUÇÃO DIRETA (para teste)
# -------------------------------

if __name__ == "__main__":
    # Configurar logging para exibir no console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Credenciais (idealmente viriam de variáveis de ambiente)
    login = "seu_login"
    senha = "sua_senha"
    
    # Executar robô
    eventos = extrair_eventos(login, senha)
    
    # Mostrar resumo
    print(f"\nResumo final: {len(eventos)} eventos encontrados")  # ALTERADO: removido 📋
    for i, evento in enumerate(eventos[:5]):  # Mostrar apenas os primeiros 5
        print(f"  {i+1}. {evento['data']} - {evento['titulo']}")