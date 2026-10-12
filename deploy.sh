#!/bin/sh
# Copy the built mirrors into ~/web, where Caddy serves them: the landing
# page at mczone.co, the main (v4) edition at v4.mczone.co and the older
# designs at v1/v2/v3.mczone.co and TerraScape at v0.mczone.co.
set -e
cd "$(dirname "$0")"
rsync -a --delete site-v4/ ~/web/mczone-site/
cp routes-v4.caddy ~/web/mczone-routes.caddy
mkdir -p ~/web/mczone-editions
for e in v0 v1 v2 v3; do
  [ -d "site-$e" ] || continue
  rsync -a --delete "site-$e/" ~/web/mczone-editions/$e/
  cp "routes-$e.caddy" ~/web/mczone-editions/routes-$e.caddy
done
python3 landing_stamp.py
rsync -a --delete --exclude incoming landing/ ~/web/mczone-editions/landing/
docker compose -f ~/web/docker-compose.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
