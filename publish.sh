#!/bin/bash
set -e

python3 export_web.py

git add docs/data.json
git commit -m "update data" 2>/dev/null || echo "No changes to commit."
git push

echo "Done — Netlify will deploy automatically."
