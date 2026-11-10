# AutoEmail - Automação de Prospecção B2B

Ferramenta desktop (Tkinter) para processar leads exportados e automatizar envio de e-mails personalizados por segmento.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📥 Download Rápido (Windows)

> **Não precisa instalar Python.** Baixe o `.exe` pronto:

👉 **[Releases mais recente](../../releases/latest)** → Baixe `AutoEmail.exe`

---

## 🚀 Como Usar no Windows (Passo a Passo)

### 1. Baixar e Preparar
1. Acesse a página de **[Releases](../../releases)**
2. Baixe o arquivo `AutoEmail.exe` (versão mais recente)
3. Crie uma pasta no seu computador, ex: `C:\AutoEmail`
4. Mova o `AutoEmail.exe` para essa pasta

### 2. Primeira Execução
1. Dê **duplo clique** no `AutoEmail.exe`
2. ⚠️ **Se o Windows bloquear**: "Windows protegeu seu PC" → clique em **Mais informações** → **Executar mesmo assim**
3. O programa abre e cria automaticamente na pasta:
   - `config.json` (configurações)
   - `historico.csv` (controle de envios)

### 3. Configurar Gmail (Obrigatório para envio real)
1. Na aba **⚙️ Configurações**, preencha:
   - **E-mail Gmail**: `seu.email@gmail.com`
   - **App Password**: gere em [Google Account → Segurança → App Passwords](https://myaccount.google.com/apppasswords)
     - Ative **Verificação em 2 etapas** primeiro
     - Selecione "Outro" → nomeie "AutoEmail" → copie a senha de 16 caracteres (sem espaços)
   - **E-mail Gestor (CC)**: e-mail para receber cópia (opcional)
   - **Assinatura**: texto que vai no rodapé dos e-mails
2. Clique em **💾 Salvar Configurações**
3. Teste com **🔌 Testar Conexão Gmail**

### 4. Importar Leads
**Opção A - CSV (recomendado):**
1. Exporte seus leads de qualquer fonte → arquivo CSV
2. Na aba **📋 Leads** → clique em **📂 Importar CSV **
3. Selecione o arquivo exportado
4. O sistema classifica automaticamente por segmento (energia, rodovia, tecnologia, etc.)

**Opção B - Adicionar manual:**
1. Na aba **📋 Leads** → preencha Nome, E-mail, Empresa, Cargo
2. Escolha Segmento → **➕ Adicionar**

### 5. Personalizar Templates (Opcional)
- Aba **📝 Templates** → escolha segmento → edite texto/assunto
- Variáveis disponíveis: `{nome}`, `{primeiro_nome}`, `{empresa}`, `{cargo}`, `{artigo}` (a/o)
- Clique **💾 Salvar Template**

### 6. Enviar E-mails
1. Aba **📧 Envio em Lote**
2. (Opcional) Marque **Forçar reenvio** se quiser reenviar para contatos já enviados
3. Clique **🚀 ENVIAR E-MAILS EM LOTE**
4. Acompanhe progresso na barra e log
5. Use **⏹️ PARAR ENVIO** se precisar interromper

### 7. Ver Histórico
- Aba **📜 Histórico** → vê todos os envios (sucesso/falha/duplicado)
- **📥 Exportar CSV** para backup/planilha

---

## 📋 Formato do CSV Esperado

O sistema aceita exportação direta(colunas: `list_name`, `email_type`, `email_status`, `email`, `full_name`, `first_name`, `last_name`, `title`, `company`, etc.)

Ou formato simplificado:
```csv
Nome,Empresa,Email,Cargo
João Silva,Empresa XYZ,joao@xyz.com.br,Diretor
Maria Santos,ABC Ltda,maria@abc.com.br,Gerente
```


## 🛠️ Build Local (Desenvolvedores)

### Windows
```powershell
git clone https://github.com/SEU_USUARIO/AutoEmail.git
cd AutoEmail
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --onefile --windowed --name "AutoEmail" `
  --add-data "config.json;." `
  --add-data "assinatura.png;." `
  --add-data "historico.csv;." `
  --hidden-import tkinter `
  --hidden-import tkinter.ttk `
  --hidden-import tkinter.scrolledtext `
  --hidden-import tkinter.filedialog `
  --hidden-import tkinter.messagebox `
  desktop_app.py
# Executável em: dist\AutoEmail.exe
```

### Linux (cross-build não suportado - use GitHub Actions)
```bash
# Só roda nativamente no Linux
python3 desktop_app.py
```

---

## 📁 Estrutura do Projeto

```
AutoEmail/
├── desktop_app.py          # Interface Tkinter (principal)
├── app.py                  # Backend compartilhado (CSV, email, histórico)
├── config.json             # Configurações (criado automaticamente)
├── historico.csv           # Log de envios (criado automaticamente)
├── assinatura.png          # Imagem da assinatura (opcional)
├── exemplo_leads.csv       # Exemplo de formato CSV
├── .github/workflows/
│   └── build-windows.yml   # Build automático Windows
├── .gitignore
└── README.md               # Este arquivo
```

---

## 🔧 Solução de Problemas

| Problema | Solução |
|----------|---------|
| `VCRUNTIME140.dll` não encontrado | Instale [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| "Windows protegeu seu PC" | Mais informações → Executar mesmo assim |
| Erro autenticação Gmail | Verifique: 2FA ativo + App Password correta (sem espaços) |
| E-mails não enviam | Veja logs na aba Envio / verifique horário e limite diário |
| Tkinter não abre | Windows N/KN precisa "Media Feature Pack" ou use Windows Pro |

---

## 🔒 Segurança

- **Nunca commite** `config.json` com senhas reais
- Use **App Password**, nunca sua senha normal do Google
- O `.gitignore` já bloqueia arquivos sensíveis
- Para distribuir: gere `.exe` limpo (sem seu `config.json` real)

---

## 📄 Licença

MIT - Uso livre para fins comerciais e pessoais.

---

## 🤝 Suporte

- Abra uma [Issue](../../issues) para bugs/sugestões
- Logs de erro ficam na aba **📧 Envio em Lote** (área de texto)
- Para dúvidas de Gmail: veja [Google App Passwords Help](https://support.google.com/accounts/answer/185833)

---
