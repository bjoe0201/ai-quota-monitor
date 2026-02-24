# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Build standalone executable (Windows .exe / macOS .app)
pyinstaller build.spec
# Output: dist/AI額度監控.exe  (or dist/AI額度監控.app on macOS)
```

There is no test suite in this project.

## Architecture

This is a Python 3.11+ tkinter desktop application that monitors AI service quota usage. The app has two data acquisition paths: a **browser data path** (currently active) and an **API path** (service classes exist but are not wired into `gui/app.py`).

### Data Flow

**Browser path (active):**
1. User installs `ai-monitor-client.js` as a Tampermonkey userscript
2. The script scrapes pages (OpenAI billing, claude.ai usage, platform.claude.com billing, GitHub Copilot settings) and POSTs JSON to `http://localhost:7890/update`
3. `services/local_server.py` receives the POST and stores it in the module-level `DATA_STORE` dict keyed by `source` field
4. `MainApp._poll_browser_live()` runs every 1.5s, checks `DATA_STORE` for new timestamps, and spawns threads to call `BrowserXxxService.fetch()` which reads from `DATA_STORE`
5. Results are put on `_result_queue`; `_poll_queue()` runs every 200ms on the main thread to call `ServiceCard.update_result()`

**Threading model:** All `service.fetch()` calls run in daemon threads. Results are communicated back to the main (GUI) thread exclusively through `queue.Queue`, which is drained by `after(200, _poll_queue)`.

### Key Modules

- **`main.py`** — Entry point; handles PyInstaller `sys._MEIPASS` path fixup, then starts `MainApp`
- **`gui/app.py`** — `MainApp(tk.Tk)` owns the window, cards, refresh logic, and settings dialog. `SERVICES` list at the top defines active services. `BROWSER_SERVICE_SOURCES` maps service keys to `DATA_STORE` source keys
- **`gui/widgets.py`** — `ServiceCard` widget with `update_result()`, `set_loading()`. `_format_data()` contains hardcoded display logic branched by `service_name` string. `COLORS` dict defines the dark theme (Catppuccin-inspired)
- **`services/base.py`** — `BaseService` ABC with `fetch(config) → ServiceResult`. `ServiceResult` is a dataclass with `service_name`, `success`, `data: dict`, `error`
- **`services/local_server.py`** — `ThreadingHTTPServer` on `127.0.0.1:7890`. Module-level `DATA_STORE: dict[str, dict]` is the shared store. `start(port)` / `stop()` / `is_running()` / `get_data(key)` are the public API
- **`services/browser_data.py`** — Four `BaseService` subclasses (one per monitored page) that read from `local_server.DATA_STORE`. Also stamps `updated_at` and adds a stale warning if data is >10 minutes old
- **`config/manager.py`** — `ConfigManager` reads/writes `~/.config/ai-quota-monitor/config.json`. Sensitive fields (tokens, API keys) are Base64-encoded on disk (not encrypted). `load()` merges saved config with `DEFAULT_CONFIG` so new keys always have defaults
- **`ai-monitor-client.js`** — Tampermonkey userscript. Runs page-specific scrapers (`parseOpenAIBilling`, `parseClaudeUsage`, `parseClaudeBilling`, `parseGitHubCopilot`) and POSTs to the local server. Has an in-page floating UI (📊 button) for status and settings

### Inactive Service Classes

`services/` contains API-based service classes (`claude_api.py`, `claude_web.py`, `github_copilot.py`, `github_copilot_web.py`, `openai_api.py`, `google_gemini.py`) that are **not** in `gui/app.py`'s `SERVICES` list. To reactivate a service, add it to both `SERVICES` and `BROWSER_SERVICE_SOURCES` (or adapt `refresh_all` to call it directly).

### Adding a New Service

1. Create `services/your_service.py` with a class extending `BaseService`; set `name` and implement `fetch(config) → ServiceResult`
2. Add a config entry in `config/manager.py`'s `DEFAULT_CONFIG["services"]`
3. Add the service instance to `SERVICES` in `gui/app.py`
4. Add display logic for `service_name` in `ServiceCard._format_data()` in `gui/widgets.py`

### Config File Location

- Windows: `C:\Users\<user>\.config\ai-quota-monitor\config.json`
- macOS/Linux: `~/.config/ai-quota-monitor/config.json`
