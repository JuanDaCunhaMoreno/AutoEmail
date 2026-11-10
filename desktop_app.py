#!/usr/bin/env python3
"""
Interface Desktop para Automação de Prospecção AutoEmail.
Usa tkinter para uma experiência nativa sem necessidade de servidor web.
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import csv
import base64
from datetime import datetime

# Importa funções do backend
from app import processar_csv, enviar_email, verificar_duplicidade, salvar_historico, carregar_historico, salvar_config, carregar_config, pode_enviar

class ProspeccaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoEmail")
        self.root.geometry("900x700")

        # Carrega configurações e histórico
        self.config = carregar_config()
        self.historico = carregar_historico()
        self.leads = []

        # Cria abas
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Aba Leads
        self.tab_leads = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_leads, text="📋 Leads")
        self.criar_aba_leads()

        # Aba Envio
        self.tab_envio = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_envio, text="📧 Envio em Lote")
        self.criar_aba_envio()

        # Aba Configurações
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="⚙️ Configurações")
        self.criar_aba_config()

        # Aba Templates
        self.tab_templates = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_templates, text="📝 Templates")
        self.criar_aba_templates()

        # Aba Histórico
        self.tab_historico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_historico, text="📜 Histórico")
        self.criar_aba_historico()

        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

    def _on_tab_changed(self, event=None):
        if self.notebook.index(self.notebook.select()) == self.notebook.index(self.tab_historico):
            self.historico = carregar_historico()
            self.atualizar_historico()

    def criar_aba_leads(self):
        # Frame superior: Upload e Adicionar Manual
        frame_top = ttk.LabelFrame(self.tab_leads, text="Importar Leads")
        frame_top.pack(fill='x', padx=10, pady=5)

        btn_upload = ttk.Button(frame_top, text="📂 Importar CSV", command=self.importar_csv)
        btn_upload.pack(side='left', padx=10, pady=10)

        self.lbl_status = ttk.Label(frame_top, text="Nenhum lead carregado")
        self.lbl_status.pack(side='left', padx=10)

        # Frame Adicionar Manual
        frame_manual = ttk.LabelFrame(self.tab_leads, text="Adicionar Lead Manualmente")
        frame_manual.pack(fill='x', padx=10, pady=5)

        grid = ttk.Frame(frame_manual)
        grid.pack(fill='x', padx=10, pady=5)

        ttk.Label(grid, text="Nome:").grid(row=0, column=0, sticky='w')
        self.entry_nome = ttk.Entry(grid, width=30)
        self.entry_nome.grid(row=0, column=1, padx=5)

        ttk.Label(grid, text="E-mail:").grid(row=0, column=2, sticky='w')
        self.entry_email = ttk.Entry(grid, width=30)
        self.entry_email.grid(row=0, column=3, padx=5)

        ttk.Label(grid, text="Empresa:").grid(row=1, column=0, sticky='w')
        self.entry_empresa = ttk.Entry(grid, width=30)
        self.entry_empresa.grid(row=1, column=1, padx=5)

        ttk.Label(grid, text="Cargo:").grid(row=1, column=2, sticky='w')
        self.entry_cargo = ttk.Entry(grid, width=30)
        self.entry_cargo.grid(row=1, column=3, padx=5)

        ttk.Label(grid, text="Segmento:").grid(row=2, column=0, sticky='w')
        self.combo_segmento = ttk.Combobox(grid, values=['tecnologia', 'energia', 'rodovia', 'saneamento', 'saude', 'educacao', 'financeiro', 'varejo', 'outros'], width=27)
        self.combo_segmento.set('tecnologia')
        self.combo_segmento.grid(row=2, column=1, padx=5)

        ttk.Label(grid, text="Artigo (a/o):").grid(row=2, column=2, sticky='w')
        self.combo_artigo = ttk.Combobox(grid, values=['a', 'o'], width=5)
        self.combo_artigo.set('a')
        self.combo_artigo.grid(row=2, column=3, padx=5, sticky='w')

        btn_add = ttk.Button(grid, text="➕ Adicionar", command=self.adicionar_lead_manual)
        btn_add.grid(row=3, column=3, pady=5)

        # Frame para tabela e botões
        frame_table = ttk.Frame(self.tab_leads)
        frame_table.pack(fill='both', expand=True, padx=10, pady=5)

        cols = ('nome', 'empresa', 'email', 'cargo', 'segmento', 'artigo')
        self.tree_leads = ttk.Treeview(frame_table, columns=cols, show='headings', height=15)
        for col in cols:
            self.tree_leads.heading(col, text=col.capitalize())
            self.tree_leads.column(col, width=60 if col == 'artigo' else 140)

        scrollbar = ttk.Scrollbar(frame_table, orient='vertical', command=self.tree_leads.yview)
        self.tree_leads.configure(yscrollcommand=scrollbar.set)

        self.tree_leads.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        frame_btn_leads = ttk.Frame(self.tab_leads)
        frame_btn_leads.pack(pady=5)

        btn_excluir_lead = ttk.Button(frame_btn_leads, text="🗑️ Excluir Selecionado", command=self.excluir_lead_selecionado)
        btn_excluir_lead.pack(side='left', padx=5)

    def criar_aba_envio(self):
        frame_info = ttk.Frame(self.tab_envio)
        frame_info.pack(fill='x', padx=10, pady=10)

        self.lbl_total_leads = ttk.Label(frame_info, text="Leads na fila: 0")
        self.lbl_total_leads.pack(anchor='w')

        self.chk_forcar = ttk.Checkbutton(frame_info, text="Forçar reenvio de duplicados")
        self.chk_forcar.pack(anchor='w', pady=5)

        frame_template = ttk.Frame(frame_info)
        frame_template.pack(anchor='w', pady=5)
        ttk.Label(frame_template, text="Template:").pack(side='left')
        self.combo_envio_template = ttk.Combobox(
            frame_template,
            values=['automatico', 'generico', 'tecnologia', 'energia', 'rodovia', 'saneamento', 'saude', 'educacao', 'financeiro', 'varejo', 'outros'],
            width=20
        )
        self.combo_envio_template.set('automatico')
        self.combo_envio_template.pack(side='left', padx=5)

        frame_botoes_envio = ttk.Frame(self.tab_envio)
        frame_botoes_envio.pack(pady=20)

        self.btn_enviar = ttk.Button(frame_botoes_envio, text="🚀 ENVIAR E-MAILS EM LOTE", command=self.iniciar_envio_lote)
        self.btn_enviar.pack(side='left', padx=5)

        self.btn_parar = ttk.Button(frame_botoes_envio, text="⏹️ PARAR ENVIO", command=self.parar_envio, state='disabled')
        self.btn_parar.pack(side='left', padx=5)

        # Progress bar e log de envio (ficam na aba Envio)
        self.progress = ttk.Progressbar(self.tab_envio, mode='determinate')
        self.progress.pack(fill='x', padx=20, pady=10)

        self.txt_log_envio = scrolledtext.ScrolledText(self.tab_envio, height=20)
        self.txt_log_envio.pack(fill='both', expand=True, padx=10, pady=10)

        self._parar_envio = False

        # Fila thread-safe para atualizações de UI
        self._ui_queue = []
        self._ui_queue_lock = threading.Lock()
        self._process_ui_queue()

    def _process_ui_queue(self):
        """Processa fila de callbacks de UI na thread principal."""
        with self._ui_queue_lock:
            callbacks = self._ui_queue[:]
            self._ui_queue.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logging.error(f"Erro em callback UI: {e}")
        self.root.after(50, self._process_ui_queue)

    def _schedule_ui(self, callback):
        """Agenda callback para rodar na thread principal."""
        with self._ui_queue_lock:
            self._ui_queue.append(callback)

    def criar_aba_config(self):
        frame = ttk.Frame(self.tab_config)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Gmail
        ttk.Label(frame, text="E-mail Gmail:").grid(row=0, column=0, sticky='w')
        self.entry_gmail = ttk.Entry(frame, width=50)
        self.entry_gmail.insert(0, self.config.get('gmail_email', ''))
        self.entry_gmail.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="App Password:").grid(row=1, column=0, sticky='w')
        self.entry_senha = ttk.Entry(frame, width=50, show='*')
        self.entry_senha.insert(0, self.config.get('gmail_app_password', ''))
        self.entry_senha.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="E-mail Gestor (CC):").grid(row=2, column=0, sticky='w')
        self.entry_gestor = ttk.Entry(frame, width=50)
        self.entry_gestor.insert(0, self.config.get('gestor_email', ''))
        self.entry_gestor.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="Assinatura (texto):").grid(row=3, column=0, sticky='nw')
        self.txt_assinatura = scrolledtext.ScrolledText(frame, width=48, height=4, wrap='word')
        self.txt_assinatura.insert('1.0', self.config.get('assinatura_empresa', ''))
        self.txt_assinatura.grid(row=3, column=1, pady=5)

        ttk.Label(frame, text="Imagem da Assinatura:").grid(row=4, column=0, sticky='w')
        frame_img = ttk.Frame(frame)
        frame_img.grid(row=4, column=1, sticky='w', pady=5)
        self.lbl_assinatura_img = ttk.Label(frame_img, text=os.path.basename(self.config.get('assinatura_imagem', '')) or '(nenhuma imagem)')
        self.lbl_assinatura_img.pack(side='left')
        btn_upload_assinatura = ttk.Button(frame_img, text="📷 Escolher Imagem", command=self.upload_assinatura_imagem)
        btn_upload_assinatura.pack(side='left', padx=10)

        ttk.Separator(frame, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky='ew', pady=10)

        # Regras
        ttk.Label(frame, text="Limite Diário:").grid(row=6, column=0, sticky='w')
        self.spin_limite = ttk.Spinbox(frame, from_=1, to=200, width=10)
        self.spin_limite.delete(0, 'end')
        self.spin_limite.insert(0, self.config.get('limite_diario', 50))
        self.spin_limite.grid(row=6, column=1, sticky='w', pady=5)

        ttk.Label(frame, text="Intervalo (minutos):").grid(row=7, column=0, sticky='w')
        self.spin_intervalo = ttk.Spinbox(frame, from_=1, to=60, width=10)
        self.spin_intervalo.delete(0, 'end')
        self.spin_intervalo.insert(0, self.config.get('intervalo_minutos', 3))
        self.spin_intervalo.grid(row=7, column=1, sticky='w', pady=5)

        ttk.Label(frame, text="Horário Início:").grid(row=8, column=0, sticky='w')
        self.spin_horario_inicio = ttk.Spinbox(frame, from_=0, to=23, width=10)
        self.spin_horario_inicio.delete(0, 'end')
        self.spin_horario_inicio.insert(0, self.config.get('horario_inicio', 8))
        self.spin_horario_inicio.grid(row=8, column=1, sticky='w', pady=5)

        ttk.Label(frame, text="Horário Fim:").grid(row=9, column=0, sticky='w')
        self.spin_horario_fim = ttk.Spinbox(frame, from_=0, to=24, width=10)
        self.spin_horario_fim.delete(0, 'end')
        self.spin_horario_fim.insert(0, self.config.get('horario_fim', 18))
        self.spin_horario_fim.grid(row=9, column=1, sticky='w', pady=5)

        self.chk_dias_uteis = ttk.Checkbutton(frame, text="Apenas dias úteis")
        if self.config.get('dias_uteis_apenas', True):
            self.chk_dias_uteis.state(['selected'])
        self.chk_dias_uteis.grid(row=10, column=0, columnspan=2, sticky='w', pady=5)

        btn_testar = ttk.Button(frame, text="🔌 Testar Conexão Gmail", command=self.testar_conexao_gmail)
        btn_testar.grid(row=11, column=0, padx=5, pady=20)

        btn_salvar = ttk.Button(frame, text="💾 Salvar Configurações", command=self.salvar_configuracoes)
        btn_salvar.grid(row=11, column=1, padx=5, pady=20)

    def criar_aba_templates(self):
        frame_top = ttk.Frame(self.tab_templates)
        frame_top.pack(fill='x', padx=10, pady=5)

        ttk.Label(frame_top, text="Segmento:").pack(side='left')
        self.combo_template_segmento = ttk.Combobox(
            frame_top,
            values=['generico', 'tecnologia', 'energia', 'rodovia', 'saneamento', 'saude', 'educacao', 'financeiro', 'varejo', 'outros'],
            width=20
        )
        self.combo_template_segmento.set('generico')
        self.combo_template_segmento.pack(side='left', padx=5)
        self.combo_template_segmento.bind('<<ComboboxSelected>>', self.carregar_template_selecionado)

        btn_salvar_template = ttk.Button(frame_top, text="💾 Salvar Template", command=self.salvar_template)
        btn_salvar_template.pack(side='left', padx=10)

        ttk.Label(frame_top, text="Assunto:").pack(side='left', padx=(20, 0))
        self.entry_template_assunto = ttk.Entry(frame_top, width=50)
        self.entry_template_assunto.pack(side='left', padx=5)

        ttk.Label(self.tab_templates, text="Corpo do E-mail (variáveis: {nome}, {empresa}, {cargo}):").pack(anchor='w', padx=10, pady=(5, 0))
        self.txt_template = scrolledtext.ScrolledText(self.tab_templates, height=22, wrap='word')
        self.txt_template.pack(fill='both', expand=True, padx=10, pady=5)

        self.carregar_template_selecionado()

    def carregar_template_selecionado(self, event=None):
        segmento = self.combo_template_segmento.get()
        textos = self.config.get('textos_segmentos', {})
        assuntos = self.config.get('assuntos_segmentos', {})
        if segmento == 'generico':
            conteudo = textos.get('generico', 'Olá {nome},\n\nGostaríamos de apresentar nossas soluções para a {empresa}.\n\nAtenciosamente,')
        else:
            conteudo = textos.get(segmento, '')
        self.txt_template.delete('1.0', 'end')
        self.txt_template.insert('1.0', conteudo)
        self.entry_template_assunto.delete(0, 'end')
        self.entry_template_assunto.insert(0, assuntos.get(segmento, ''))

    def salvar_template(self):
        segmento = self.combo_template_segmento.get()
        conteudo = self.txt_template.get('1.0', 'end').strip()
        assunto = self.entry_template_assunto.get().strip()
        if 'textos_segmentos' not in self.config:
            self.config['textos_segmentos'] = {}
        if 'assuntos_segmentos' not in self.config:
            self.config['assuntos_segmentos'] = {}
        self.config['textos_segmentos'][segmento] = conteudo
        self.config['assuntos_segmentos'][segmento] = assunto
        salvar_config(self.config)
        messagebox.showinfo("Sucesso", f"Template '{segmento}' salvo!")

    def criar_aba_historico(self):
        cols = ('data', 'nome', 'email', 'empresa', 'status')
        self.tree_hist = ttk.Treeview(self.tab_historico, columns=cols, show='headings', height=22)
        for col in cols:
            self.tree_hist.heading(col, text=col.capitalize())
            self.tree_hist.column(col, width=150)

        self.tree_hist.pack(fill='both', expand=True, padx=10, pady=(10, 5))

        frame_botoes = ttk.Frame(self.tab_historico)
        frame_botoes.pack(pady=5)

        btn_refresh = ttk.Button(frame_botoes, text="🔄 Atualizar", command=self.atualizar_historico)
        btn_refresh.pack(side='left', padx=5)

        btn_exportar = ttk.Button(frame_botoes, text="📥 Exportar CSV", command=self.exportar_historico_csv)
        btn_exportar.pack(side='left', padx=5)

        btn_excluir_hist = ttk.Button(frame_botoes, text="🗑️ Excluir Selecionado", command=self.excluir_historico_selecionado)
        btn_excluir_hist.pack(side='left', padx=5)

        self.atualizar_historico()

    # --- Métodos de Ação ---

    @staticmethod
    def detectar_artigo(empresa):
        nome = (empresa or '').strip().lower()
        masculinos = ['banco', 'grupo', 'mercado', 'supermercado', 'atacado', 'atacarejo',
                      'hospital', 'hotel', 'restaurante', 'bar', 'clube', 'condomínio',
                      'escritório', 'estúdio', 'laboratório', 'município', 'estado',
                      'ministério', 'departamento', 'instituto', 'centro', 'parque',
                      'shopping', 'aeroporto', 'porto', 'terminal', 'estádio', 'museu',
                      'teatro', 'cinema', 'jornal', 'canal', 'sistema', 'programa',
                      'projeto', 'serviço', 'produto', 'aplicativo', 'app']
        femininos = ['empresa', 'indústria', 'fábrica', 'loja', 'rede', 'marca',
                     'plataforma', 'solução', 'consultoria', 'assessoria', 'agência',
                     'operadora', 'concessionária', 'distribuidora', 'transportadora',
                     'seguradora', 'financeira', 'imobiliária', 'construtora', 'incorporadora',
                     'faculdade', 'universidade', 'escola', 'creche', 'clínica',
                     'fundação', 'associação', 'cooperativa', 'prefeitura', 'câmara',
                     'assembleia', 'secretaria', 'diretoria', 'gerência', 'coordenação']
        primeira_palavra = nome.split()[0] if nome else ''
        for m in masculinos:
            if primeira_palavra == m or nome.startswith(m + ' '):
                return 'o'
        for f in femininos:
            if primeira_palavra == f or nome.startswith(f + ' '):
                return 'a'
        return 'a'

    def importar_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not filepath:
            return

        try:
            # Usa processar_csv do app.py que já faz o mapeamento correto das colunas
            leads_processados = processar_csv(filepath, self.config)

            self.leads = []
            for lead in leads_processados:
                # Adiciona campos que o desktop_app espera
                lead['artigo'] = lead.get('artigo', '') or self.detectar_artigo(lead.get('empresa', ''))
                lead['duplicado'] = verificar_duplicidade(lead.get('email', ''), self.historico)
                self.leads.append(lead)

            self.atualizar_tabela_leads()
            self.lbl_status.config(text=f"{len(self.leads)} leads carregados")
            self.lbl_total_leads.config(text=f"Leads na fila: {len(self.leads)}")
            messagebox.showinfo("Sucesso", f"{len(self.leads)} leads importados!")

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def adicionar_lead_manual(self):
        nome = self.entry_nome.get().strip()
        email = self.entry_email.get().strip()
        empresa = self.entry_empresa.get().strip()
        cargo = self.entry_cargo.get().strip()
        segmento = self.combo_segmento.get()
        artigo = self.combo_artigo.get()

        if not nome or not email or not empresa:
            messagebox.showwarning("Atenção", "Preencha Nome, E-mail e Empresa.")
            return

        novo_lead = {
            'nome': nome,
            'email': email,
            'empresa': empresa,
            'cargo': cargo,
            'segmento': segmento,
            'artigo': artigo,
            'duplicado': verificar_duplicidade(email, self.historico)
        }

        self.leads.append(novo_lead)
        self.atualizar_tabela_leads()
        self.lbl_status.config(text=f"{len(self.leads)} leads carregados")
        self.lbl_total_leads.config(text=f"Leads na fila: {len(self.leads)}")

        # Limpa campos
        self.entry_nome.delete(0, 'end')
        self.entry_email.delete(0, 'end')
        self.entry_empresa.delete(0, 'end')
        self.entry_cargo.delete(0, 'end')

        messagebox.showinfo("Sucesso", "Lead adicionado!")

    def atualizar_tabela_leads(self):
        for item in self.tree_leads.get_children():
            self.tree_leads.delete(item)
        for lead in self.leads:
            tag = 'dup' if lead.get('duplicado') else ''
            self.tree_leads.insert('', 'end', values=(
                lead.get('nome', ''),
                lead.get('empresa', ''),
                lead.get('email', ''),
                lead.get('cargo', ''),
                lead.get('segmento', ''),
                lead.get('artigo', 'a')
            ), tags=(tag,))
        self.tree_leads.tag_configure('dup', background='#ffcccc')

    def iniciar_envio_lote(self):
        if not self.leads:
            messagebox.showwarning("Atenção", "Nenhum lead na fila.")
            return

        if not self.config.get('gmail_email') or not self.config.get('gmail_app_password'):
            messagebox.showerror("Erro", "Configure o Gmail na aba Configurações primeiro.")
            return

        self._schedule_ui(lambda: self.btn_enviar.config(state='disabled'))
        self.progress['maximum'] = len(self.leads)
        self.progress['value'] = 0
        self.txt_log_envio.delete('1.0', 'end')

        thread = threading.Thread(target=self.executar_envios, daemon=True)
        thread.start()

    def parar_envio(self):
        self._parar_envio = True
        self._log_ui("\n⏹️ Parando envio após o e-mail atual...")
        self._schedule_ui(lambda: self.btn_parar.config(state='disabled'))

    def executar_envios(self):
        enviados = 0
        falhas = 0
        forcar = self.chk_forcar.instate(['selected'])
        self._parar_envio = False
        self._schedule_ui(lambda: self.btn_parar.config(state='normal'))
        self._schedule_ui(lambda: self.btn_enviar.config(state='disabled'))

        for i, lead in enumerate(self.leads):
            if self._parar_envio:
                self._log_ui("\n⏹️ Envio interrompido pelo usuário.")
                break

            self.config = carregar_config()
            email = lead.get('email', '')

            if not forcar and verificar_duplicidade(email, self.historico):
                self._log_ui(f"[DUPLICADO] {email} - Já enviado anteriormente.")
                continue

            pode, motivo = pode_enviar(self.config, self.historico)
            if not pode:
                self._log_ui(f"[BLOQUEADO] {motivo}")
                break

            template_escolhido = self.combo_envio_template.get()
            segmento_envio = lead.get('segmento', 'outros') if template_escolhido == 'automatico' else template_escolhido

            self._log_ui(f"Enviando para {email} (template: {segmento_envio})...")
            sucesso, msg = enviar_email(
                self.config,
                email,
                lead.get('nome', ''),
                lead.get('empresa', ''),
                segmento_envio,
                cargo=lead.get('cargo', ''),
                artigo=lead.get('artigo', 'a')
            )

            registro = {
                'nome': lead.get('nome', ''),
                'empresa': lead.get('empresa', ''),
                'email': email,
                'cargo': lead.get('cargo', ''),
                'segmento': lead.get('segmento', 'outros'),
                'data_envio': datetime.now().isoformat(),
                'status': 'enviado' if sucesso else 'falha',
                'assunto': f"Proposta de parceria - {lead.get('empresa', '')}"
            }
            self.historico.append(registro)
            try:
                salvar_historico(self.historico)
            except Exception as e:
                self._log_ui(f"⚠️ ERRO AO SALVAR HISTÓRICO: {e}")
            self._schedule_ui(self.atualizar_historico)

            if sucesso:
                enviados += 1
                self._log_ui(f"✅ SUCESSO: {email}")
            else:
                falhas += 1
                self._log_ui(f"❌ FALHA: {email} - {msg}")

            self._schedule_ui(lambda v=i+1: self.progress.config(value=v))

            # Intervalo
            if i < len(self.leads) - 1 and sucesso:
                import time
                intervalo = self.config.get('intervalo_minutos', 3) * 60
                self._log_ui(f"Aguardando {intervalo}s...")
                time.sleep(intervalo)

        self._schedule_ui(lambda: self.btn_enviar.config(state='normal'))
        self._schedule_ui(lambda: self.btn_parar.config(state='disabled'))
        self._parar_envio = False

        self._log_ui(f"\n--- CONCLUÍDO ---\nEnviados: {enviados} | Falhas: {falhas}")
        self._schedule_ui(lambda: messagebox.showinfo("Concluído", f"Envios finalizados.\nSucessos: {enviados}\nFalhas: {falhas}"))

    def _log_ui(self, msg):
        """Log thread-safe para a área de envio."""
        self._schedule_ui(lambda m=msg: self._log_envio_direct(m))

    def _log_envio_direct(self, msg):
        """Log direto (deve ser chamado via _schedule_ui)."""
        self.txt_log_envio.insert('end', msg + '\n')
        self.txt_log_envio.see('end')

    def log_envio(self, msg):
        """Compatibilidade: redireciona para thread-safe."""
        self._log_ui(msg)

    def testar_conexao_gmail(self):
        email = self.entry_gmail.get().strip()
        senha = self.entry_senha.get().strip()

        if not email or not senha:
            messagebox.showwarning("Atenção", "Preencha o e-mail e a App Password primeiro.")
            return

        import smtplib
        import socket

        dominio = email.split('@')[-1] if '@' in email else ''
        is_workspace = dominio and dominio != 'gmail.com'

        # Diagnóstico passo a passo
        diagnostico = []

        # Passo 1: Verifica DNS
        try:
            socket.getaddrinfo('smtp.gmail.com', 465)
            diagnostico.append("✅ DNS: smtp.gmail.com resolvido")
        except socket.gaierror:
            messagebox.showerror("Erro de Rede", "Não foi possível resolver smtp.gmail.com.\nVerifique sua conexão com a internet.")
            return

        # Passo 2: Testa conexão TCP porta 465
        tcp_465 = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('smtp.gmail.com', 465))
            sock.close()
            tcp_465 = True
            diagnostico.append("✅ Porta 465: acessível")
        except Exception as e:
            diagnostico.append(f"❌ Porta 465: {type(e).__name__}")

        # Passo 3: Testa conexão TCP porta 587
        tcp_587 = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('smtp.gmail.com', 587))
            sock.close()
            tcp_587 = True
            diagnostico.append("✅ Porta 587: acessível")
        except Exception as e:
            diagnostico.append(f"❌ Porta 587: {type(e).__name__}")

        if not tcp_465 and not tcp_587:
            messagebox.showerror("Bloqueio de Rede", "Ambas as portas SMTP (465 e 587) estão bloqueadas.\n\nIsso pode ser causado por:\n• Firewall corporativo bloqueando SMTP\n• Antivírus com proteção de e-mail ativa\n• Provedor de internet bloqueando portas de envio\n\nTente usar uma rede diferente (ex: hotspot do celular) para confirmar.")
            return

        # Passo 4: Tenta autenticação SMTP
        conectado = False
        metodo = ""
        erro_auth = None

        if tcp_465:
            try:
                servidor = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
                servidor.ehlo()
                servidor.login(email, senha)
                servidor.quit()
                conectado = True
                metodo = "SSL (porta 465)"
            except smtplib.SMTPAuthenticationError as e:
                erro_auth = str(e)
            except Exception as e:
                diagnostico.append(f"⚠️ SSL falhou: {type(e).__name__}: {e}")

        if not conectado and tcp_587:
            try:
                servidor = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(email, senha)
                servidor.quit()
                conectado = True
                metodo = "STARTTLS (porta 587)"
            except smtplib.SMTPAuthenticationError as e:
                erro_auth = str(e)
            except Exception as e:
                diagnostico.append(f"⚠️ STARTTLS falhou: {type(e).__name__}: {e}")

        if conectado:
            messagebox.showinfo("Sucesso", f"Conexão com Gmail estabelecida!\nMétodo: {metodo}\nCredenciais válidas.")
            return

        # Se chegou aqui, falhou a autenticação
        msg_erro = "Falha na autenticação SMTP.\n\n"
        if erro_auth:
            msg_erro += f"Detalhe: {erro_auth}\n\n"

        if is_workspace:
            msg_erro += (
                f"Sua conta é Google Workspace ({dominio}).\n\n"
                "O administrador da organização pode ter:\n"
                "• Desativado o acesso SMTP para apps menos seguros\n"
                "• Bloqueado App Passwords no painel admin\n"
                "• Exigido OAuth2 em vez de SMTP\n\n"
                "Soluções:\n"
                "1. Peça ao admin do Google Workspace para liberar SMTP\n"
                "2. Gere uma nova App Password em:\n   myaccount.google.com/apppasswords\n"
                "3. Use uma conta @gmail.com pessoal para testes"
            )
        else:
            msg_erro += (
                "Verifique:\n"
                "1. App Password copiada corretamente (16 chars, sem espaços)\n"
                "2. Verificação em duas etapas ATIVADA na conta Google\n"
                "3. Gere nova App Password em:\n   myaccount.google.com/apppasswords\n\n"
                "Se já tentou várias vezes, o Google pode ter bloqueado\n"
                "temporariamente. Aguarde 1 hora e tente novamente."
            )

        diagnostico_str = "\n".join(diagnostico)
        messagebox.showerror("Falha na Conexão", f"{msg_erro}\n\n--- Diagnóstico ---\n{diagnostico_str}")

    def salvar_configuracoes(self):
        self.config['gmail_email'] = self.entry_gmail.get()
        self.config['gmail_app_password'] = self.entry_senha.get()
        self.config['gestor_email'] = self.entry_gestor.get()
        self.config['assinatura_empresa'] = self.txt_assinatura.get('1.0', 'end').strip()
        self.config['limite_diario'] = int(self.spin_limite.get())
        self.config['intervalo_minutos'] = int(self.spin_intervalo.get())
        self.config['horario_inicio'] = int(self.spin_horario_inicio.get())
        self.config['horario_fim'] = int(self.spin_horario_fim.get())
        self.config['dias_uteis_apenas'] = bool(self.chk_dias_uteis.instate(['selected']))

        try:
            salvar_config(self.config)
            messagebox.showinfo("Sucesso", "Configurações salvas!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar configurações:\n{str(e)}")

    def upload_assinatura_imagem(self):
        filepath = filedialog.askopenfilename(
            title="Escolher Imagem da Assinatura",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif")]
        )
        if not filepath:
            return
        import shutil
        # Usa o mesmo diretório do config (writable em ambos os modos)
        if getattr(sys, 'frozen', False):
            destino_dir = os.path.dirname(sys.executable)
        else:
            destino_dir = os.path.dirname(os.path.abspath(__file__))
        destino = os.path.join(destino_dir, 'assinatura.png')
        try:
            shutil.copy2(filepath, destino)
            self.config['assinatura_imagem'] = destino
            salvar_config(self.config)
            self.lbl_assinatura_img.config(text='assinatura.png')
            messagebox.showinfo("Sucesso", "Imagem da assinatura salva!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar imagem:\n{str(e)}")

    def atualizar_historico(self):
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)
        for idx, reg in enumerate(reversed(self.historico)):
            data = reg.get('data_envio', '')[:19].replace('T', ' ')
            self.tree_hist.insert('', 'end', values=(
                data,
                reg.get('nome', ''),
                reg.get('email', ''),
                reg.get('empresa', ''),
                reg.get('status', '')
            ), tags=(str(len(self.historico) - 1 - idx),))

    def excluir_lead_selecionado(self):
        selected = self.tree_leads.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um lead para excluir.")
            return
        indices = []
        for item in selected:
            idx = self.tree_leads.index(item)
            indices.append(idx)
        for idx in sorted(indices, reverse=True):
            email = self.leads[idx].get('email', '')
            self.historico = [r for r in self.historico if r.get('email') != email]
            try:
                salvar_historico(self.historico)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar histórico:\n{e}")
                return
            del self.leads[idx]
        self.atualizar_tabela_leads()
        self.lbl_status.config(text=f"{len(self.leads)} leads carregados")
        self.lbl_total_leads.config(text=f"Leads na fila: {len(self.leads)}")
        messagebox.showinfo("Sucesso", f"{len(indices)} lead(s) excluído(s) e removido(s) do histórico.")

    def excluir_historico_selecionado(self):
        selected = self.tree_hist.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
            return
        indices_to_remove = set()
        for item in selected:
            tags = self.tree_hist.item(item, 'tags')
            if tags:
                indices_to_remove.add(int(tags[0]))
        self.historico = [r for i, r in enumerate(self.historico) if i not in indices_to_remove]
        try:
            salvar_historico(self.historico)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar histórico:\n{e}")
            return
        self.atualizar_historico()
        messagebox.showinfo("Sucesso", f"{len(indices_to_remove)} registro(s) excluído(s) do histórico.")

    def exportar_historico_csv(self):
        if not self.historico:
            messagebox.showwarning("Atenção", "Nenhum registro no histórico para exportar.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="historico_exportado.csv"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['Nome', 'Empresa', 'Email', 'Cargo'])
                for reg in self.historico:
                    writer.writerow([
                        reg.get('nome', ''),
                        reg.get('empresa', ''),
                        reg.get('email', ''),
                        reg.get('cargo', '')
                    ])
            messagebox.showinfo("Sucesso", f"Histórico exportado com sucesso!\nArquivo: {filepath}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProspeccaoApp(root)
    root.mainloop()