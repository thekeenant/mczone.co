# mczone-archive

Source for mczone.co, an archive of the MC Zone Minecraft network (2012 to 2013).

- `landing/` is the page served at mczone.co.
- `scrape.py` rebuilds the old websites from the Wayback Machine:
  `v4.mczone.co` (Jul to Nov 2013) plus `v1` to `v3` for the older designs.
- `fill/` holds stock library files the captures are missing.
- `site-v1/` to `site-v4/` are the built mirrors, with
  `routes*.caddy` mapping old URLs to files. Player email addresses are
  blanked during the build.
- `caddy/mczone.caddy` is a copy of the mczone.co blocks from `~/web/Caddyfile`.

## Commands

```sh
python3 scrape.py fetch [v1|v2|v3|v4] # download captures into raw/ (default v4)
python3 scrape.py build [v1|v2|v3|v4] # write site-<edition>/ and routes-<edition>.caddy
./deploy.sh                           # sync everything into ~/web and reload Caddy
./deploy_landing.sh                   # sync only the landing page
```

Wayback downloads (`raw/`, `avatars/`) are not tracked; see `.gitignore`.
