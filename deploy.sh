#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-tennispi}"
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/pi/Tennis/backup_slider_${STAMP}"

if [[ ! "$TARGET" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid SSH target: $TARGET" >&2
  exit 2
fi

FILES=(
  control_server.py
  index.html
  pca_ch1_30pct.py
  pca_sweep_independant.py
  tennis
)

for file in "${FILES[@]}"; do
  if [ ! -f "$PROJECT_DIR/$file" ]; then
    echo "Missing local file: $PROJECT_DIR/$file" >&2
    exit 1
  fi
done

echo "Checking SSH connection to $TARGET..."
ssh -o BatchMode=yes -o ConnectTimeout=8 "$TARGET" 'hostname'

STAGE_DIR="$(ssh "$TARGET" 'mktemp -d /home/pi/Tennis/.deploy.XXXXXX')"
if [[ ! "$STAGE_DIR" =~ ^/home/pi/Tennis/\.deploy\.[A-Za-z0-9]+$ ]]; then
  echo "Unexpected staging path: $STAGE_DIR" >&2
  exit 1
fi

cleanup() {
  ssh "$TARGET" "rm -f '$STAGE_DIR/control_server.py' '$STAGE_DIR/index.html' '$STAGE_DIR/pca_ch1_30pct.py' '$STAGE_DIR/pca_sweep_independant.py' '$STAGE_DIR/tennis'; rmdir '$STAGE_DIR' 2>/dev/null || true" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Uploading to staging directory..."
scp "$PROJECT_DIR/control_server.py" "$TARGET:$STAGE_DIR/control_server.py"
scp "$PROJECT_DIR/index.html" "$TARGET:$STAGE_DIR/index.html"
scp "$PROJECT_DIR/pca_ch1_30pct.py" "$TARGET:$STAGE_DIR/pca_ch1_30pct.py"
scp "$PROJECT_DIR/pca_sweep_independant.py" "$TARGET:$STAGE_DIR/pca_sweep_independant.py"
scp "$PROJECT_DIR/tennis" "$TARGET:$STAGE_DIR/tennis"

echo "Validating staged files..."
ssh "$TARGET" "python3 -m py_compile '$STAGE_DIR/control_server.py' '$STAGE_DIR/pca_ch1_30pct.py' '$STAGE_DIR/pca_sweep_independant.py' && bash -n '$STAGE_DIR/tennis'"

echo "Forcing all PCA9685 channels off..."
ssh "$TARGET" '/home/pi/.local/bin/tennis off'

echo "Backing up current controller to $BACKUP_DIR..."
ssh "$TARGET" "mkdir -p '$BACKUP_DIR' && cp /home/pi/Tennis/control_server.py '$BACKUP_DIR/control_server.py' && cp /home/pi/Tennis/web/index.html '$BACKUP_DIR/index.html' && cp /home/pi/Tennis/pca_ch1_30pct.py '$BACKUP_DIR/pca_ch1_30pct.py' && cp /home/pi/Tennis/pca_sweep_independant.py '$BACKUP_DIR/pca_sweep_independant.py' && cp /home/pi/.local/bin/tennis '$BACKUP_DIR/tennis'"

echo "Installing validated files..."
ssh "$TARGET" "install -m 644 '$STAGE_DIR/control_server.py' /home/pi/Tennis/control_server.py && install -m 644 '$STAGE_DIR/index.html' /home/pi/Tennis/web/index.html && install -m 755 '$STAGE_DIR/pca_ch1_30pct.py' /home/pi/Tennis/pca_ch1_30pct.py && install -m 755 '$STAGE_DIR/pca_sweep_independant.py' /home/pi/Tennis/pca_sweep_independant.py && install -m 755 '$STAGE_DIR/tennis' /home/pi/.local/bin/tennis"

echo "Restarting the web controller..."
ssh "$TARGET" 'sudo systemctl restart tennis-control.service'
sleep 2

echo "Verifying service and API..."
ssh "$TARGET" 'systemctl is-active tennis-control.service && curl -fsS http://192.168.99.1:8080/api/status'

echo
echo "Deployment complete. Motors remain off."
echo "Backup: $BACKUP_DIR"
