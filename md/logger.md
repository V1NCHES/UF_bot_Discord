# Data Logging & Synchronization (`logger.py`)

This module handles all data persistence operations, ensuring that event data and member balances are saved both locally and in the cloud.

## Key Features
- **Google Sheets Integration**:
    - **Event Logging**: Uses a 3-column layout per call (ID/Date, Organizer/Nick, Empty Separator).
    - **Smart Column Management**: 
        - For new calls, it checks if the first columns are empty (e.g., after deletion) to reuse them, or inserts 3 new columns at Column A.
        - For existing calls, it finds the previously assigned columns and updates the data in place.
    - **Data Clearing**: When an event is deleted in Discord, the bot finds its columns and wipes the data, making the space available for reuse.
    - **Balance Management**: Manages the "Balance" sheet for tracking member shares and total balances.
    - **Member Sync**: Handles the "UF" sheet for synchronizing server member lists.
- **Balance Management Utilities**:
    - `add_content_shares`: Inserts new columns for "splits" and updates member records. It splits incoming text line-by-line: Line 1 goes to E1 (first row), Line 2 goes to E2 (second row), and subsequent lines are processed line-by-line (ID, Nick, Amount) to find the row by ID and save the amount into Column E.
    - `update_balance_rows`: Adds new server members to the Balance sheet with summation formulas starting from Column D.
    - `archive_balance_sheet`: Transfers current balances (Column C) to the archive (Column D) and clears active split columns (E+).
    - `withdraw_user_balance`: Handles individual payouts by resetting a user's active balance to 0, clearing active split columns (E+), and inserting a structured transaction log row directly into `LogBalance` at `index=1` (the very top row) with Treasurer information.
    - `get_spreadsheet_id`: Dynamically reads the customized Google Spreadsheet ID from `settings.json`, falling back to `config.SPREADSHEET_ID` if unset.
    - `get_attendance_stats`: Analyzes event participation over the last week or month using ID-based tracking.
    - `sort_uf_sheet` / `sort_balance_sheet`: Ensures data remains organized alphabetically by nickname.
    - `get_user_balance`: Retrieves a specific user's balance from the spreadsheet.
    - `export_balance_sheet`: Creates an Excel backup before balance modifications (e.g., before `/split`, `/balance_archive`, or `/withdraw_money`).

## Asynchronous Operations
All Google Sheets operations are wrapped in `asyncio.to_thread` to ensure the bot remains responsive. Data types are carefully managed to ensure numbers are saved as numeric types in the spreadsheet (avoiding leading quotes).
