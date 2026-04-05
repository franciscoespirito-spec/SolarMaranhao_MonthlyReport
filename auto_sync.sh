#!/bin/bash
# Auto-commit and push on file changes
WATCH_DIR="/root/projetos"
LOG="/root/projetos/.auto_sync.log"

echo "[$(date)] Auto-sync iniciado. Monitorando: $WATCH_DIR" >> "$LOG"

inotifywait -m -r -e modify,create,delete,move \
  --exclude '(\.git|\.auto_sync\.log)' \
  "$WATCH_DIR" 2>/dev/null | while read -r dir event file; do
    # Aguarda 3s para acumular múltiplas alterações simultâneas
    sleep 3
    cd "$WATCH_DIR" || exit
    if [[ -n $(git status --porcelain) ]]; then
      git add -A
      COMMIT_MSG="auto: $(date '+%Y-%m-%d %H:%M:%S') - $event $file"
      git commit -m "$COMMIT_MSG" >> "$LOG" 2>&1
      git push origin main >> "$LOG" 2>&1
      echo "[$(date)] Sincronizado: $COMMIT_MSG" >> "$LOG"
    fi
done
