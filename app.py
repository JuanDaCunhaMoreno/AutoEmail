#!/usr/bin/env python3
"""
Backend principal da ferramenta de automação de prospecção AutoEmail.
Processa CSV, classifica segmentos, envia e-mails via Gmail e gerencia histórico.
"""

import csv
import json
import logging
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import StringIO
from urllib.parse import urlparse, parse_qs
import threading
import time
import re


def get_base_path():
    """
    Retorna o caminho base da aplicação, funcionando tanto em desenvolvimento
    quanto no executável PyInstaller (frozen).
    """
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller: usa sys._MEIPASS (diretório temporário de extração)
        # ou o diretório do executável para arquivos de dados persistentes
        return sys._MEIPASS
    else:
        # Desenvolvimento: diretório do script
        return os.path.dirname(os.path.abspath(__file__))


def get_data_path(filename):
    """
    Retorna o caminho completo para um arquivo de dados, funcionando em ambos os modos.
    """
    base = get_base_path()
    return os.path.join(base, filename)

# Configuração de logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'prospeccao.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Caminhos dos arquivos - usam funções que funcionam em ambos os modos
CONFIG_FILE = get_data_path('config.json')
HISTORICO_FILE = get_data_path('historico.csv')

# Segmentos padrão e regras de classificação
SEGMENTOS_PADRAO = {
    'energia': ['energia', 'elétrica', 'eletrica', 'power', 'geração', 'geracao', 'distribuição', 'distribuicao', 'transmissão', 'transmissao', 'renovável', 'renovavel', 'solar', 'eólica', 'eolica'],
    'rodovia': ['rodovia', 'estrada', 'concessionária', 'concessionaria', 'pedágio', 'pedagio', 'transporte', 'logística', 'logistica', 'infraestrutura'],
    'saneamento': ['saneamento', 'água', 'agua', 'esgoto', 'tratamento', 'resíduos', 'residuos', 'ambiental', 'recursos hídricos', 'hidricos'],
    'tecnologia': ['tecnologia', 'tech', 'software', 'digital', 'inovação', 'inovacao', 'TI', 'informática', 'informatica', 'dados', 'cloud', 'startup'],
    'saúde': ['saúde', 'saude', 'hospital', 'clínica', 'clinica', 'médico', 'medico', 'farmacêutica', 'farmaceutica', 'biotech', 'vida'],
    'educação': ['educação', 'educacao', 'ensino', 'escola', 'universidade', 'faculdade', 'curso', 'treinamento', 'capacitação', 'capacitacao'],
    'financeiro': ['banco', 'finança', 'financa', 'crédito', 'credito', 'investimento', 'seguro', 'fintech', 'pagamento', 'cobrança'],
    'varejo': ['varejo', 'comércio', 'comercio', 'loja', 'retail', 'distribuidor', 'atacado', 'e-commerce', 'ecommerce']
}

def get_config_path():
    """
    Retorna o caminho onde o config.json deve ser salvo (escrita).
    Em modo frozen, salva no diretório do executável.
    Em desenvolvimento, salva no diretório do script.
    """
    if getattr(sys, 'frozen', False):
        # Executável: salva no mesmo diretório do executável (writable)
        return os.path.join(os.path.dirname(sys.executable), 'config.json')
    else:
        # Desenvolvimento: salva no diretório do script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


def carregar_config():
    """Carrega configurações do arquivo JSON."""
    # Tenta carregar do local de escrita primeiro (config do usuário)
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Fallback: carrega do bundle (apenas leitura, config padrão)
    bundle_config = get_data_path('config.json')
    if os.path.exists(bundle_config):
        with open(bundle_config, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Configuração padrão se não encontrar nenhum
    return {
        'gmail_email': '',
        'gmail_app_password': '',
        'gestor_email': '',
        'assinatura_empresa': '',
        'limite_diario': 50,
        'intervalo_minutos': 3,
        'horario_inicio': 8,
        'horario_fim': 18,
        'dias_uteis_apenas': True,
        'textos_segmentos': {},
        'regras_classificacao': SEGMENTOS_PADRAO.copy()
    }


def salvar_config(config):
    """Salva configurações no arquivo JSON (local writable)."""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_historico_path():
    """
    Retorna o caminho onde o historico.csv deve ser salvo (escrita).
    Em modo frozen, salva no diretório do executável.
    Em desenvolvimento, salva no diretório do script.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'historico.csv')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'historico.csv')


def carregar_historico():
    """Carrega histórico de envios do CSV."""
    historico = []
    # Tenta carregar do local de escrita primeiro
    historico_path = get_historico_path()
    if os.path.exists(historico_path):
        with open(historico_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                historico.append(row)
        return historico

    # Fallback: carrega do bundle (apenas leitura)
    bundle_historico = get_data_path('historico.csv')
    if os.path.exists(bundle_historico):
        with open(bundle_historico, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                historico.append(row)
    return historico


def salvar_historico(historico):
    """Salva histórico de envios no CSV (local writable)."""
    historico_path = get_historico_path()
    fieldnames = ['nome', 'empresa', 'email', 'cargo', 'segmento', 'data_envio', 'status', 'assunto']
    with open(historico_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in historico:
            writer.writerow(row)

def classificar_segmento(nome_empresa, cargo, regras):
    """Classifica o segmento da empresa baseado em regras."""
    texto = f"{nome_empresa} {cargo}".lower()

    for segmento, palavras_chave in regras.items():
        for palavra in palavras_chave:
            if palavra.lower() in texto:
                return segmento

    return 'outros'

def verificar_duplicidade(email, historico):
    """Verifica se o e-mail já foi enviado anteriormente."""
    for registro in historico:
        if registro['email'].lower() == email.lower():
            return True
    return False

def pode_enviar(config, historico):
    """Verifica se pode enviar e-mail baseado nas regras."""
    # Verifica horário
    agora = datetime.now()
    if config.get('dias_uteis_apenas', True) and agora.weekday() >= 5:
        return False, 'Hoje não é dia útil'

    hora_atual = agora.hour
    if hora_atual < config.get('horario_inicio', 8) or hora_atual >= config.get('horario_fim', 18):
        return False, 'Fora do horário permitido'

    # Verifica limite diário
    hoje = agora.strftime('%Y-%m-%d')
    envios_hoje = sum(1 for reg in historico
                     if reg.get('data_envio', '').startswith(hoje) and reg['status'] == 'enviado')

    if envios_hoje >= config.get('limite_diario', 50):
        return False, f'Limite diário atingido ({envios_hoje}/{config["limite_diario"]})'

    return True, 'OK'

def resolver_caminho_imagem(img_path):
    """
    Resolve o caminho da imagem da assinatura, funcionando em ambos os modos.
    Verifica: 1) caminho absoluto do config, 2) diretório do executável, 3) bundle (sys._MEIPASS)
    """
    if not img_path:
        return None

    # 1. Se é caminho absoluto e existe, usa direto
    if os.path.isabs(img_path) and os.path.exists(img_path):
        return img_path

    # 2. Tenta relativo ao executável (para imagens salvas pelo usuário)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidate = os.path.join(exe_dir, os.path.basename(img_path))
        if os.path.exists(candidate):
            return candidate

    # 3. Tenta no bundle (sys._MEIPASS)
    bundle_path = get_data_path(os.path.basename(img_path))
    if os.path.exists(bundle_path):
        return bundle_path

    # 4. Tenta no diretório do script (desenvolvimento)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, os.path.basename(img_path))
    if os.path.exists(candidate):
        return candidate

    return None


def enviar_email(config, destinatario, nome, empresa, segmento, cargo='', artigo='a'):
    """Envia e-mail personalizado via Gmail (ou simula em modo teste)."""
    try:
        modo_teste = not config.get('gmail_email') or not config.get('gmail_app_password')

        if modo_teste:
            logger.info(f"[MODO TESTE] E-mail simulado para {destinatario} ({empresa}) - Segmento: {segmento}")
            return True, 'Enviado com sucesso (MODO TESTE - nenhum e-mail real enviado)'

        primeiro_nome = nome.split()[0] if nome else ''

        assuntos = config.get('assuntos_segmentos', {})
        assunto_template = assuntos.get(segmento, '') or "Proposta de parceria - {empresa}"
        assunto = assunto_template.replace('{nome}', nome).replace('{primeiro_nome}', primeiro_nome).replace('{empresa}', empresa).replace('{cargo}', cargo or '').replace('{artigo}', artigo or 'a')

        texto_base = config.get('textos_segmentos', {}).get(segmento, '')
        if not texto_base:
            texto_base = f"Olá {nome},\n\nGostaríamos de apresentar nossas soluções para a {empresa}.\n\nAtenciosamente,"
        corpo_texto = texto_base.replace('{nome}', nome).replace('{primeiro_nome}', primeiro_nome).replace('{empresa}', empresa).replace('{cargo}', cargo or '').replace('{artigo}', artigo or 'a')
        assinatura_texto = config.get('assinatura_empresa', '')
        if assinatura_texto:
            corpo_texto += f"\n\n{assinatura_texto}"

        corpo_html = corpo_texto.replace('\n', '<br>')
        img_path = config.get('assinatura_imagem', '')
        resolved_img_path = resolver_caminho_imagem(img_path)
        if resolved_img_path and os.path.exists(resolved_img_path):
            with open(img_path, 'rb') as f:
                img_data = f.read()
            ext = os.path.splitext(img_path)[1].lower()
            mime_type = 'image/png' if ext == '.png' else ('image/gif' if ext == '.gif' else 'image/jpeg')
            img_cid = 'assinatura_img'
            corpo_html += f'<br><br><img src="cid:{img_cid}" alt="Assinatura">'
            msg = MIMEMultipart('related')
            msg_alt = MIMEMultipart('alternative')
            msg_alt.attach(MIMEText(corpo_texto, 'plain', 'utf-8'))
            msg_alt.attach(MIMEText(corpo_html, 'html', 'utf-8'))
            msg.attach(msg_alt)
            from email.mime.image import MIMEImage
            img_part = MIMEImage(img_data, _subtype=mime_type.split('/')[-1])
            img_part.add_header('Content-ID', f'<{img_cid}>')
            img_part.add_header('Content-Disposition', 'inline', filename='assinatura.png')
            msg.attach(img_part)
        else:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(corpo_texto, 'plain', 'utf-8'))
            msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

        # Suporte a múltiplos CCs (separados por vírgula) com fallback para formato antigo
        gestor_emails_raw = config.get('gestor_email', '')
        gestor_emails = [e.strip() for e in gestor_emails_raw.split(',') if e.strip()]

        msg['From'] = config['gmail_email']
        msg['To'] = destinatario
        if gestor_emails:
            msg['Cc'] = ', '.join(gestor_emails)
        msg['Subject'] = assunto

        # Tenta enviar via SMTP_SSL (porta 465) ou STARTTLS (porta 587)
        texto_completo = msg.as_string()
        destinatarios = [destinatario]
        destinatarios.extend(gestor_emails)

        enviado = False
        # Método 1: SSL direto na porta 465
        try:
            servidor = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
            servidor.ehlo()
            servidor.login(config['gmail_email'], config['gmail_app_password'])
            servidor.sendmail(config['gmail_email'], destinatarios, texto_completo)
            servidor.quit()
            enviado = True
        except Exception as e_ssl:
            logger.warning(f"Falha via SSL (465): {e_ssl}. Tentando STARTTLS (587)...")
            # Método 2: STARTTLS na porta 587
            try:
                servidor = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(config['gmail_email'], config['gmail_app_password'])
                servidor.sendmail(config['gmail_email'], destinatarios, texto_completo)
                servidor.quit()
                enviado = True
            except Exception as e_tls:
                raise e_tls

        logger.info(f"E-mail enviado para {destinatario} ({empresa})")
        return True, 'Enviado com sucesso'

    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {destinatario}: {str(e)}")
        return False, str(e)

def processar_csv(arquivo_csv, config):
    """Processa arquivo CSV e retorna leads classificados."""
    leads = []

    with open(arquivo_csv, 'r', encoding='utf-8-sig') as f:
        conteudo = f.read()

    # Detecta delimitador (vírgula ou ponto-e-vírgula)
    if ';' in conteudo.split('\n')[0]:
        delimitador = ';'
    else:
        delimitador = ','

    reader = csv.DictReader(StringIO(conteudo), delimiter=delimitador)

    for row in reader:
        # Inicializa com valores vazios
        row_normalizado = {
            'nome': '',
            'empresa': '',
            'email': '',
            'cargo': ''
        }

        # Mapeamento EXATO das colunas
        # Email - procura coluna exata 'email'
        if 'email' in row:
            row_normalizado['email'] = row['email'].strip() if row['email'] else ''

        # Nome - usa full_name ou first_name + last_name
        if 'full_name' in row and row['full_name']:
            row_normalizado['nome'] = row['full_name'].strip()
        elif 'first_name' in row:
            primeiro = row['first_name'].strip() if row['first_name'] else ''
            ultimo = row.get('last_name', '').strip() if row.get('last_name') else ''
            row_normalizado['nome'] = f"{primeiro} {ultimo}".strip()

        # Empresa - usa coluna exata 'company'
        if 'company' in row and row['company']:
            row_normalizado['empresa'] = row['company'].strip()

        # Cargo - usa coluna exata 'title'
        if 'title' in row and row['title']:
            row_normalizado['cargo'] = row['title'].strip()

        # Só adiciona se tiver email válido (com @)
        if row_normalizado['email'] and '@' in row_normalizado['email']:
            segmento = classificar_segmento(
                row_normalizado.get('empresa', ''),
                row_normalizado.get('cargo', ''),
                config.get('regras_classificacao', SEGMENTOS_PADRAO)
            )
            row_normalizado['segmento'] = segmento
            leads.append(row_normalizado)

    return leads

class ProspeccaoHandler(BaseHTTPRequestHandler):
    """Handler HTTP para a interface web."""

    def __init__(self, *args, **kwargs):
        self.config = carregar_config()
        self.historico = carregar_historico()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Trata requisições GET."""
        parsed = urlparse(self.path)

        if parsed.path == '/api/config':
            self.send_json(self.config)
        elif parsed.path == '/api/historico':
            self.send_json(self.historico)
        elif parsed.path == '/api/status':
            status = {
                'configurado': bool(self.config.get('gmail_email') and self.config.get('gmail_app_password')),
                'leads_carregados': 0,
                'envios_hoje': self._contar_envios_hoje()
            }
            self.send_json(status)
        elif parsed.path == '/' or parsed.path == '/interface.html':
            self.enviar_interface_html()
        else:
            self.send_error(404)

    def do_POST(self):
        """Trata requisições POST."""
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        if parsed.path == '/api/config':
            dados = json.loads(body)
            self.config.update(dados)
            salvar_config(self.config)
            self.send_json({'status': 'ok'})

        elif parsed.path == '/api/upload':
            # Processa upload de CSV
            import tempfile
            import base64

            try:
                dados = json.loads(body)
                csv_content = base64.b64decode(dados['content'])

                # Decodifica como string UTF-8
                csv_text = csv_content.decode('utf-8')

                # Cria arquivo temporário com conteúdo texto
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as f:
                    f.write(csv_text)
                    temp_path = f.name

                try:
                    leads = processar_csv(temp_path, self.config)
                    os.unlink(temp_path)

                    # Marca duplicados
                    for lead in leads:
                        lead['duplicado'] = verificar_duplicidade(lead['email'], self.historico)

                    self.send_json({'leads': leads, 'total': len(leads)})
                except Exception as e:
                    os.unlink(temp_path)
                    logger.error(f"Erro ao processar CSV: {str(e)}")
                    self.send_json({'error': str(e)}, 500)
            except Exception as e:
                logger.error(f"Erro ao fazer upload do CSV: {str(e)}")
                self.send_json({'error': str(e)}, 500)

        elif parsed.path == '/api/enviar':
            dados = json.loads(body)
            email_destino = dados.get('email')
            nome = dados.get('nome', '')
            empresa = dados.get('empresa', '')
            segmento = dados.get('segmento', 'outros')

            # Verifica duplicidade
            if not dados.get('forcar_reenvio', False) and verificar_duplicidade(email_destino, self.historico):
                self.send_json({'status': 'duplicado', 'mensagem': 'E-mail já enviado anteriormente'})
                return

            # Verifica se pode enviar
            pode, motivo = pode_enviar(self.config, self.historico)
            if not pode:
                self.send_json({'status': 'bloqueado', 'mensagem': motivo})
                return

            # Envia o e-mail
            sucesso, mensagem = enviar_email(self.config, email_destino, nome, empresa, segmento)

            # Registra no histórico
            registro = {
                'nome': nome,
                'empresa': empresa,
                'email': email_destino,
                'cargo': dados.get('cargo', ''),
                'segmento': segmento,
                'data_envio': datetime.now().isoformat(),
                'status': 'enviado' if sucesso else 'falha',
                'assunto': f"Proposta de parceria - {empresa}"
            }
            self.historico.append(registro)
            salvar_historico(self.historico)

            self.send_json({
                'status': 'enviado' if sucesso else 'falha',
                'mensagem': mensagem
            })

        elif parsed.path == '/api/adicionar-lead':
            dados = json.loads(body)
            email = dados.get('email', '').strip().lower()

            # Verifica duplicidade simples no histórico
            for h in self.historico:
                if h.get('email', '').lower() == email:
                    self.send_json({'error': 'Este e-mail já está no histórico de envios.'})
                    return

            # Retorna sucesso para o frontend adicionar na memória local
            self.send_json({'status': 'ok', 'mensagem': 'Lead adicionado à lista local.'})

        elif parsed.path == '/api/enviar-lote':
            logger.info(f"DEBUG: Body recebido (primeiros 500 chars): {body[:500]}")
            dados = json.loads(body)
            leads = dados.get('leads', [])
            logger.info(f"DEBUG: Total de leads recebidos no backend: {len(leads)}")
            if leads:
                logger.info(f"DEBUG: Primeiro lead recebido: {leads[0]}")

            resultados = {
                'enviados': 0,
                'falhas': 0,
                'duplicados': 0,
                'detalhes': []
            }

            for i, lead in enumerate(leads):
                # Verifica duplicidade
                if lead.get('duplicado') and not dados.get('forcar_reenvio', False):
                    resultados['duplicados'] += 1
                    resultados['detalhes'].append({
                        'email': lead['email'],
                        'status': 'duplicado'
                    })
                    continue

                # Verifica limites
                pode, motivo = pode_enviar(self.config, self.historico)
                if not pode:
                    resultados['detalhes'].append({
                        'email': lead['email'],
                        'status': 'bloqueado',
                        'motivo': motivo
                    })
                    break

                # Verifica se está em modo de teste (sem credenciais)
                gmail_email = self.config.get('gmail_email', '')
                gmail_password = self.config.get('gmail_app_password', '')

                if not gmail_email or not gmail_password:
                    # MODO TESTE: Simula sucesso sem enviar e-mail real
                    sucesso = True
                    mensagem = "Enviado com sucesso (MODO TESTE - Sem credenciais)"
                    logger.info(f"MODO TESTE: Simulando envio para {lead['email']}")
                else:
                    # Envio real via Gmail
                    sucesso, mensagem = enviar_email(
                        self.config,
                        lead['email'],
                        lead.get('nome', ''),
                        lead.get('empresa', ''),
                        lead.get('segmento', 'outros')
                    )

                # Registra no histórico
                registro = {
                    'nome': lead.get('nome', ''),
                    'empresa': lead.get('empresa', ''),
                    'email': lead['email'],
                    'cargo': lead.get('cargo', ''),
                    'segmento': lead.get('segmento', 'outros'),
                    'data_envio': datetime.now().isoformat(),
                    'status': 'enviado' if sucesso else 'falha',
                    'assunto': f"Proposta de parceria - {lead.get('empresa', '')}"
                }
                self.historico.append(registro)
                salvar_historico(self.historico)

                if sucesso:
                    resultados['enviados'] += 1
                else:
                    resultados['falhas'] += 1

                resultados['detalhes'].append({
                    'email': lead['email'],
                    'status': 'enviado' if sucesso else 'falha',
                    'mensagem': mensagem
                })

                # Em modo teste, não espera intervalo para ser mais rápido
                if sucesso and gmail_email and gmail_password:
                    if i < len(leads) - 1:
                        intervalo = self.config.get('intervalo_minutos', 3) * 60
                        time.sleep(intervalo)

            self.send_json(resultados)

        elif parsed.path == '/api/exportar-historico':
            self.exportar_historico_csv()

        else:
            self.send_error(404)

    def _contar_envios_hoje(self):
        """Conta quantos e-mails foram enviados hoje."""
        hoje = datetime.now().strftime('%Y-%m-%d')
        return sum(1 for reg in self.historico
                  if reg.get('data_envio', '').startswith(hoje) and reg['status'] == 'enviado')

    def enviar_interface_html(self):
        """Envia o arquivo HTML da interface."""
        html_path = os.path.join(os.path.dirname(__file__), 'interface.html')
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.send_error(404, 'Interface HTML não encontrada')

    def exportar_historico_csv(self):
        """Exporta histórico como CSV."""
        output = StringIO()
        if self.historico:
            fieldnames = self.historico[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.historico:
                writer.writerow(row)

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Content-Disposition', 'attachment; filename="historico_prospeccao.csv"')
        self.end_headers()
        self.wfile.write(output.getvalue().encode('utf-8'))

    def send_json(self, data, status_code=200):
        """Envia resposta JSON."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        """Sobrescreve log para usar nosso logger."""
        logger.info("%s - %s" % (self.client_address[0], format % args))

def iniciar_servidor(porta=8080):
    """Inicia o servidor HTTP."""
    import socketserver
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    servidor = ReusableTCPServer(('localhost', porta), ProspeccaoHandler)
    logger.info(f"Servidor iniciado em http://localhost:{porta}")
    print(f"\n{'='*60}")
    print(f"AutoEmail iniciado!")
    print(f"Acesse: http://localhost:{porta}")
    print(f"{'='*60}\n")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor encerrado")
        servidor.server_close()

if __name__ == '__main__':
    porta = 8080
    if len(sys.argv) > 1:
        try:
            porta = int(sys.argv[1])
        except ValueError:
            pass

    iniciar_servidor(porta)