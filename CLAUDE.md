# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`SolarMaranhao_MonthlyReport` — Monthly report project for SolarMaranhao.

## GitHub Repository

- **URL:** https://github.com/franciscoespirito-spec/SolarMaranhao_MonthlyReport
- **Branch principal:** `main`
- **Usuário:** franciscoespirito-spec

## Sincronização Automática com GitHub

Qualquer alteração feita nos arquivos do projeto é automaticamente commitada e enviada ao GitHub.

### Como funciona

- Um serviço systemd (`solar-autosync`) monitora o diretório `/root/projetos` via `inotifywait`
- Ao detectar alterações (create, modify, delete, move), aguarda 3 segundos e faz `git add -A`, `git commit` e `git push`
- O log de sincronização fica em `/root/projetos/.auto_sync.log`

### Comandos úteis

```bash
# Ver status do serviço
systemctl status solar-autosync

# Ver log de sincronizações
tail -f /root/projetos/.auto_sync.log

# Reiniciar o serviço
systemctl restart solar-autosync

# Parar o serviço
systemctl stop solar-autosync
```

### Arquivos relevantes

- `/root/projetos/auto_sync.sh` — script de monitoramento e sync
- `/etc/systemd/system/solar-autosync.service` — definição do serviço systemd
