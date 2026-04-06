# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`SolarMaranhao_MonthlyReport` — Sistema de relatório mensal automatizado de geração solar para portfólio de 5 usinas em Barreirinhas/MA.

---

## GitHub Repository

- **URL:** https://github.com/franciscoespirito-spec/SolarMaranhao_MonthlyReport
- **Branch principal:** `main`
- **Usuário:** franciscoespirito-spec

### Criar repositório (se não existir)

Se o repositório não existir no GitHub, crie com:

```bash
gh repo create franciscoespirito-spec/SolarMaranhao_MonthlyReport \
  --public --description "Relatório mensal automatizado de geração solar - Maranhão" \
  --source /root/projetos/SolarMaranhao_MonthlyReport \
  --remote origin --push
```

Ou manualmente:
1. Acesse https://github.com/new
2. Crie o repositório `SolarMaranhao_MonthlyReport` na conta `franciscoespirito-spec`
3. Configure o remote: `git remote add origin https://github.com/franciscoespirito-spec/SolarMaranhao_MonthlyReport.git`
4. Faça o primeiro push: `git push -u origin main`

---

## Sincronização Automática com GitHub

**Qualquer alteração feita nos arquivos do projeto é automaticamente commitada e enviada ao GitHub.**

Isso inclui: criação, modificação, exclusão ou movimentação de arquivos no diretório `/root/projetos`.

### Como funciona

- Um serviço systemd (`solar-autosync`) monitora o diretório `/root/projetos` via `inotifywait`
- Ao detectar alterações (create, modify, delete, move), aguarda 3 segundos e executa:
  - `git add -A`
  - `git commit -m "auto: TIMESTAMP - TIPO ARQUIVO"`
  - `git push`
- O log de sincronização fica em `/root/projetos/.auto_sync.log`

### Comandos de gerenciamento

```bash
# Ver status do serviço
systemctl status solar-autosync

# Ver log de sincronizações em tempo real
tail -f /root/projetos/.auto_sync.log

# Reiniciar o serviço
systemctl restart solar-autosync

# Parar o serviço
systemctl stop solar-autosync

# Iniciar o serviço
systemctl start solar-autosync
```

### Arquivos do auto-sync

- `/root/projetos/auto_sync.sh` — script de monitoramento e sync
- `/etc/systemd/system/solar-autosync.service` — definição do serviço systemd

### Verificar se está funcionando

```bash
# Verificar se o serviço está ativo
systemctl is-active solar-autosync

# Verificar última sincronização
tail -1 /root/projetos/.auto_sync.log

# Verificar se os arquivos locais estão no GitHub
git log --oneline -5
git status
```

### Restaurar auto-sync (se parar de funcionar)

```bash
# Recriar o serviço
systemctl daemon-reload
systemctl enable solar-autosync
systemctl start solar-autosync
```

---

## Sincronização Automática da Planilha Excel (Google Drive)

A planilha `Historico Geracao Solar Maranhao 2026.xlsx` é mantida no Google Drive compartilhado da empresa:
- **Caminho no Drive:** `8 Geração Distribuída/15. Operação e Manutenção/`
- **Remote rclone:** `gdrive` (requer autenticação OAuth configurada uma vez)

Um timer systemd (`solar-sync-excel`) copia o arquivo do Drive para o servidor diariamente às **6h UTC** (antes do relatório das 8h).

### Configurar autenticação Google Drive (apenas uma vez)

```bash
# Rodar no terminal do servidor (requer browser para OAuth)
rclone config
# → Nome: gdrive
# → Tipo: drive
# → Scope: drive.readonly
# → Team Drive: sim (informar o ID do Drive compartilhado)
# → Seguir o link OAuth, autorizar, colar o código
```

### Comandos de gerenciamento

```bash
# Ver status do timer
systemctl status solar-sync-excel.timer

# Executar sync manualmente agora
bash /root/projetos/SolarMaranhao_MonthlyReport/sync_excel.sh

# Ver log de sincronizações
tail -f /root/projetos/SolarMaranhao_MonthlyReport/sync_excel.log

# Testar acesso ao Drive (após configurar rclone)
rclone ls "gdrive:8 Geração Distribuída/15. Operação e Manutenção"
```

### Arquivos do sync Excel
- `/root/projetos/SolarMaranhao_MonthlyReport/sync_excel.sh` — script de sync
- `/etc/systemd/system/solar-sync-excel.service` — serviço systemd
- `/etc/systemd/system/solar-sync-excel.timer` — timer diário (6h UTC)

---

## Estrutura do Projeto

```
SolarMaranhao_MonthlyReport/
├── main.py                   # CLI principal — python3 main.py [--month YYYY-MM] [--no-email]
├── config.py                 # Metadados das usinas, constantes, mapeamento Excel
├── data_loader.py            # Leitura e parsing do Excel
├── kpi_calculator.py         # Cálculo de KPIs (FC, yield, gap, degradação, financeiro)
├── chart_generator.py        # Geração de gráficos matplotlib
├── ai_analyst.py             # Integração Claude API para análises em linguagem natural
├── report_builder.py         # Montagem do PDF com ReportLab (8 seções)
├── email_sender.py           # Envio do relatório por email via SMTP Gmail
├── requirements.txt          # Dependências Python
├── output/                   # Relatórios PDF gerados
└── Historico Geracao Solar Maranhao 2026.xlsx  # Fonte de dados
```

## Como gerar o relatório manualmente

```bash
cd /root/projetos/SolarMaranhao_MonthlyReport

# Configurar variáveis de ambiente
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export GMAIL_FROM="francisco.santo@beng.eng.br"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Gerar relatório do mês anterior e enviar email
python3 main.py

# Gerar relatório de um mês específico sem email
python3 main.py --month 2026-03 --no-email

# Só calcular KPIs sem gerar PDF
python3 main.py --dry-run
```

## Agendamento automático

O relatório é gerado automaticamente no 1° dia útil de cada mês via agente remoto Claude Code.

- **ID do trigger:** `trig_01NBYjrkW17pLVH3YBgRM9d4`
- **Cron:** `0 8 1-3 * *` (dias 1-3 de cada mês às 8h UTC — o agente verifica se é dia útil)
- **Gerenciar:** https://claude.ai/code/scheduled/trig_01NBYjrkW17pLVH3YBgRM9d4
