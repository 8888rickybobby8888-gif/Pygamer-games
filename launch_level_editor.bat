@echo off
rem Starts the level editor's local server (in its own window, so you can
rem see compile/upload logs and errors) and opens the editor page once
rem it's up. Just double-click this file.

cd /d "%~dp0"
start "PyGamerPortal Level Editor Server" cmd /k node level_editor_server.js
timeout /t 2 /nobreak >nul
start "" http://localhost:8787
