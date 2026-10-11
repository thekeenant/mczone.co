#!/bin/sh
# Landing page only: stamp the stylesheet version and sync to ~/web (no Caddy reload).
set -e
cd "$(dirname "$0")"
python3 landing_stamp.py
rsync -a --delete --exclude incoming landing/ ~/web/mczone-editions/landing/
