# Project Structure: Discord Event & Balance Bot

This project is a Discord bot designed for event management (calls/raids) and member balance tracking (shares/splits), integrated with Google Sheets and Excel.

## Core Files

### 1. [main.py](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/main.py)
**Purpose:** Bot Entry Point & Command Definitions.
- Handles initialization and global state.
- Implements core slash commands and `on_message` logic for quick interactions inside event threads.

### 2. [ui.py](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/ui.py)
**Purpose:** Discord UI Components.
- Manages Views, Buttons, and Modals.
- Handles the interaction logic for event sign-ups and organization.
- **Data Clearing**: Triggers data wiping in spreadsheets when a call is deleted.

### 3. [logger.py](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/logger.py)
**Purpose:** Data Persistence & Synchronization.
- **Columnar Format:** Uses a 3-column layout (ID/Date, Name, Empty Separator) for event logging.
- **Smart Sync**: Reuses empty space in the spreadsheet before creating new columns.
- **Wiping**: Clears specific columns when an event is deleted.
- **Balance & Splits**: Manages users balance records, payouts, and line-by-line splits.

### 4. [config.py](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/config.py)
**Purpose:** Configuration & Constants.
- Manages credentials, spreadsheet IDs, and bot intents.

## Detailed Documentation
Detailed guides for each module can be found in the `md/` directory:
- [main.md](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/md/main.md)
- [ui.md](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/md/ui.md)
- [logger.md](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/md/logger.md)
- [config.md](file:///c:/Users/Ivan/Desktop/Discord%20Bot/call_UF/md/config.md)

---

## Configuration & Support Files
*   **`.env`**: Sensitive tokens.
*   **`credentials.json`**: Google Cloud service account key.
*   **`requirements.txt`**: Bot dependencies.
*   **`settings.json`**: Dynamic configurations (guild-specific channels, roles, dashboard message IDs).
*   **`objectives.json`**: Active game map objectives database.
*   **`state.json`**: Bot persistent state/cache.
*   **`calls_cache.json`**: Event sign-up template configurations cache.
