# mczone-archive

Source for mczone.co, an archive of the MC Zone Minecraft network (2012 to 2013)
and TerraScape before it (2011 to 2012).

- `landing/` is the page served at mczone.co.
- `scrape.py` rebuilds the old websites from the Wayback Machine:
  `v4.mczone.co` (Jul to Nov 2013) plus `v1` to `v3` for the older designs.
- `build_v0.py` builds `v0.mczone.co`, the TerraScape website. It was never
  captured by the Wayback Machine, so `raw/v0/` is a wget mirror of the live
  terrascapemc.weebly.com (see the command below).
- `fill/` holds stock library files the captures are missing.
- `site-v0/` to `site-v4/` are the built mirrors, with
  `routes*.caddy` mapping old URLs to files. Player email addresses are
  blanked during the build.
- `caddy/mczone.caddy` is a copy of the mczone.co blocks from `~/web/Caddyfile`.

## Commands

```sh
python3 scrape.py fetch [v1|v2|v3|v4] # download captures into raw/ (default v4)
python3 scrape.py build [v1|v2|v3|v4] # write site-<edition>/ and routes-<edition>.caddy
python3 build_v0.py                   # write site-v0/ from raw/v0/
./deploy.sh                           # sync everything into ~/web and reload Caddy
./deploy_landing.sh                   # sync only the landing page
```

Wayback downloads (`raw/`, `avatars/`) are not tracked; see `.gitignore`.
To refetch TerraScape into `raw/v0/` (all its pages, then its uploaded images):

```sh
cd raw/v0 && wget -e robots=off --page-requisites --convert-links \
  --adjust-extension --span-hosts -nH \
  --domains=terrascapemc.weebly.com,cdn2.editmysite.com,cdn11.editmysite.com \
  https://terrascapemc.weebly.com/{index,guides,online-shop,donate,plugins,gallery,contact}.html
grep -oh "uploads/[^\"' )?&]*" *.html | sort -u |
  while read p; do curl -s --create-dirs -o "$p" "https://terrascapemc.weebly.com/$p"; done
```
