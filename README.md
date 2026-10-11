# mczone-archive

Source for mczone.co, an archive of the MC Zone Minecraft network (2012 to 2013).

- `landing/` is the page served at mczone.co.
- `scrape.py` rebuilds the old websites from the Wayback Machine:
  `v4.mczone.co` (Jul to Nov 2013) plus `v1` to `v3` for the older designs.
- `fill/` holds stock library files the captures are missing.

## Commands

```sh
python3 scrape.py fetch [v1|v2|v3]    # download captures into raw/
python3 scrape.py build [v1|v2|v3]    # write site*/ and routes*.caddy
./deploy.sh                           # sync everything into ~/web and reload Caddy
./deploy_landing.sh                   # sync only the landing page
```

Downloads and build output are not tracked; see `.gitignore`.
