# One command runs the demo: `make demo` trains (seed 641, the committed run), prepares the
# data and starts the viewer (Vite prints its URL, normally http://localhost:5173). Needs uv and Node 20.19+ or 22.12+.

.PHONY: demo train web test media

demo: train web

# Regenerates web/public/replay.json. Same seed -> byte-identical file, so the committed run is kept.
train:
	cd trainer && uv run python -m trainer.train --out ../web/public/replay.json

web/node_modules/.package-lock.json: web/package-lock.json
	cd web && npm ci
	touch $@

# Installs the viewer's dependencies, copies track.json and seeds replay.json if missing, then serves.
web: web/node_modules/.package-lock.json
	cd web && npm run dev

test:
	cd trainer && uv run pytest
	cd web && npm run build && npm test

# Optional: re-records docs/media/lap.gif and docs/media/learning.gif from web/public/replay.json.
# Needs Google Chrome (or CHROME_PATH) and Python 3 with Pillow.
media: web/node_modules/.package-lock.json
	cd web && npm run build
	node scripts/make_gifs.mjs
