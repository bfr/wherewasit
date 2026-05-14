# Missä se nyt oli — Flask port

Drop-in replacement for the existing Flask app. Paper aesthetic, Finland-first
ledger, PWA-installable, service persistence preserved (localStorage), no
auto-select on first result.

## Files in this folder

```
app.py                                # replaces your existing app.py
templates/
  index.html                          # full Jinja port of the design
  offline.html                        # PWA offline fallback
static/
  styles.css                          # paper-theme CSS, baked in
  app.js                              # row expand, pill toggle, select2 persistence, SW register
  sw.js                               # service worker (network-first HTML, cache-first static)
  manifest.webmanifest                # PWA manifest
  icons/
    icon-192.png
    icon-512.png
    icon-maskable-512.png
    apple-touch-icon.png              # 180×180 for iOS
    favicon-32.png
```

## Apply

From this project, copy the whole `justwatch-port/` folder over your local
`justwatch/` checkout:

```bash
# from your repo, with the project export downloaded as justwatch-port/
cp -r justwatch-port/app.py            justwatch/app.py
cp -r justwatch-port/templates/        justwatch/templates/
cp -r justwatch-port/static/           justwatch/static/
```

Flask serves files from `static/` automatically — no extra config needed.

## What changed in `app.py`

1. **New helpers**: `svc_initials`, `country_highlight`, `summarize_finland`.
2. **`group_services`** now also tracks per-service `monetization_types` and
   tags each `by_country` entry with a `highlight` string
   (`"has-fi-subs"` / `"has-en-pair"` / `""`). Services are sorted with
   Finland-availability first, then by monetization rank.
3. **`COUNTRY_DISPLAY_ORDER`** extended to cover all 49 JustWatch markets
   (FI/Nordics first, then EU, Americas, APAC). Passed to the template.
4. **PWA routes** added: `/sw.js`, `/manifest.webmanifest`, `/offline`.
   The SW is served from the origin root with `Service-Worker-Allowed: /` so
   its scope covers the whole site.

The search → availability data flow and form contracts are unchanged, so any
bookmarks / external links keep working.

## What changed in the template

- Replaced Avenir Next / gradient bg with the paper system (Instrument Serif
  italic + DM Sans + JetBrains Mono).
- New masthead, hero card, dedicated **Finland feature** card, world-strip
  market visualization, per-country detail with FI-subs / EN-pair highlights.
- Filters use pill-buttons (monetization / audio / subs) and a single select2
  dropdown for services (kept because of the existing persistence story).
- Per-country detail is collapsed by default; click "Per-country detail" on
  any row to expand it.

## Service persistence

Same localStorage key strategy as before, key renamed to `msno_selected_services_v1`.
- Picked services survive across searches AND across browser sessions.
- If a previously-selected service isn't in the current title's offer set,
  it's still listed in the dropdown (annotated "(not in this title)") so you
  don't lose your preference.
- A "Clear remembered" button next to the services dropdown wipes the saved
  preference.

If you want to migrate your existing saved services seamlessly, add this once
on app startup in `app.js`:

```js
try {
  const old = localStorage.getItem('jw_selected_services_v1');
  if (old && !localStorage.getItem('msno_selected_services_v1')) {
    localStorage.setItem('msno_selected_services_v1', old);
  }
} catch (_) {}
```

## PWA install

- Chrome / Edge / Android: visit the app over HTTPS (or `localhost`),
  install prompt appears in the address bar.
- iOS Safari: Share → Add to Home Screen.
- The service worker precaches CSS / JS / fonts / icons / offline page.
- HTML pages: network-first; the last successful page is also cached so a
  reload while offline shows your last lookup.
- Bump `VERSION` in `static/sw.js` when you change static assets to force a
  cache refresh on next visit.

## Local dev

```bash
flask --app app run --debug
# or
python app.py
```

Service workers need HTTPS in production but work fine on `http://localhost`.

## Icons

The bundled icons are a generic terracotta tile with an italic "?" mark and
a small "M·S·N·O" word-mark in the corner — placeholder until you have a real
logo. Replace the five PNGs in `static/icons/` and you're done; sizes are
labelled in the filenames.

## Known caveats

- The hero meta line ("Feature film" vs "Series") doesn't have a strong
  source-of-truth in the current Flask response — we only know `object_type`
  from the search result, which is lost by the time you POST `availability`.
  If you want it shown, also forward `selected_object_type` as a hidden
  field in the availability form (one-line change in `templates/index.html`
  and `app.py`).
- The synopsis / poster image are still placeholders. JustWatch exposes
  both via `entry.poster` and `entry.short_description`; pipe those through
  if you want the real things.
