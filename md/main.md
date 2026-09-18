# Main Bot Script (`main.py`)

This is the entry point of the Discord bot. It initializes the bot client using Discord Slash Commands (`commands.Bot` and `app_commands`) and defines all user-facing commands and event listeners.

## Key Features
- **Bot Initialization**: Sets up the bot with required intents (messages, members, message content) and synchronizes the application command tree (`bot.tree.sync()`) upon startup.
- **Event Handling**: 
    - `on_ready`: Logs when the bot is online and synchronizes slash commands.
    - `on_message`: 
        - Handles `.+[number]` and `.-[number]` for quick self-registration or deregistration inside active event threads.
        - Handles `!+[number] [user]` for quick slot assignment by organizers inside event threads.
- **Slash Commands**:
    - `/call [ping_role] [title] [duration] [template_id]`: Creates a standard event by opening a UI configurator button. Supports template autocompletion.
    - `/call_setting [role_or_desc] [link] [roles_str]`: Quick creation of standard event.
    - `/zvz [ping_role] [title] [duration] [template_id]`: Creates a ZvZ event by opening a UI configurator button. Supports template autocompletion.
    - `/zvz_setting [role_or_desc] [link] [roles_str]`: Quick creation of ZvZ event.
    - `/roum [ping_role] [title] [duration] [template_id]`: Creates a Roum event by opening a UI configurator button. Supports template autocompletion.
    - `/roum_setting [role_or_desc] [link] [roles_str]`: Quick creation of Roum event.
    - `/save_role [role]`: (Admin) Sets a dedicated role authorized to save event templates.
    - `/withdraw_money [user]`: (Admin) Processes a withdrawal, clearing user active split data and resetting their balance to 0.
    - `/set_withdraw [channel] [role]`: (Admin) Combined command to configure the channel for withdrawal requests and/or the role to notify.
    - `/withdrawal_request`: Allows users to request a payout.
    - `/split [text]`: (Admin) Processes content shares and logs them into Google Sheets line-by-line (Line 1 -> E1, Line 2 -> E2, Line 3+ -> ID Nick Amount).
    - `/balance_update`: (Admin) Adds new server members to the Balance sheet with summation formulas.
    - `/balance_archive`: (Admin) Moves current totals to the archive column, clears active content columns, and sorts the sheet.
    - `/balance_uf`: (Admin) Displays a list of all user balances inside a beautiful monospace code block table.
    - `/balance [user]`: Allows users to check their own or another user's balance.
    - `/uf`: (Admin) Synchronizes server members with the Google Sheet, identifying missing members and sorting.
    - `/info`: Detailed help menu for all users.
    - `/info_ad`: (Admin) Help menu for administrative and financial commands.
    - `/activity [period]`: Shows user's content attendance count for a custom number of days or week/month.
    - `/activity_all [period]`: (Admin) Shows top active members with beautiful padded monospace tabular layout.
    - `/config_call [channel]`: (Admin) Configures a specific channel where the `/call` command can be executed.
    - `/config_zvz [channel] [role]`: (Admin) Configures the channel and minimum required role for ZvZ calls.
    - `/config_roum [channel] [role]`: (Admin) Configures the channel and minimum required role for Roum calls.
    - `/config_user [channel]`: (Admin) Configures a specific channel where ordinary users can execute user commands.
    - `/config_sheet [url]`: (Admin) Configures the custom Google Spreadsheet URL dynamically.
    - `/ava_portal [location]`: Allows checking Avalon portals (tier, chests, size) with custom autocompletes for 320+ locations.
    - `/ava_portal_sync`: (Admin) Manually synchronizes Avalon portal cache with the Google Spreadsheet.
    - `/regear [role] [weapon] [offhand] [head] [chest] [shoes] [cape] [screenshot]`: Allows players to submit gear compensation applications with full Russian Albion Online autocomplete.
    - `/regear_summary [days]`: Renders summary analytics for guild regears.
    - `/config_regear_channel [channel]`: (Admin) Configures the channel where regear applications are posted for officers to review.
    - `/regear_approve [id]`: (Admin) Manually approves a regear application.
    - `/regear_reject [id] [reason]`: (Admin) Manually rejects a regear application with a reason.

## Reusable Templates Cache
- All call templates are cached in `calls_cache.json` with custom user-supplied names.
- Auto-complete dropdowns retrieve choices from this cache dynamically, using a safe parse to prevent reading exceptions on empty/wiped cache files.
