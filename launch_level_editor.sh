#!/bin/sh
# Starts the level editor's local server and opens the editor page (macOS/Linux twin of launch_level_editor.bat).
cd "$(dirname "$0")" || exit 1
node level_editor_server.js &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' INT TERM
sleep 2
URL=http://localhost:8787
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; elif command -v open >/dev/null 2>&1; then open "$URL"; else echo "Open $URL in your browser."; fi
wait $SERVER
