# Configuration & Settings (`config.py`)

This file contains the core settings, constants, and environment variable loading logic for the bot.

## Key Settings
- **Environment Variables**: Uses `python-dotenv` to load the `DISCORD_TOKEN` from the `.env` file.
- **API Constants**:
    - `SPREADSHEET_ID`: The unique ID of the Google Spreadsheet used for logging.
    - `CREDENTIALS_FILE`: Path to the Google Cloud service account JSON file.
- **File Paths**: Defines the name of the local Excel backup file (`calls_log.xlsx`).
- **Discord Intents**: Configures `discord.Intents` to allow the bot to read message content and member lists.
- **Dynamic Configurations (`settings.json`)**:
    - `user_channel_id`: Designated channel where ordinary users can invoke commands.
    - `withdraw_channel_id` / `withdraw_role_id`: Channel and role for withdrawal request notifications.
    - `spreadsheet_id` / `spreadsheet_url`: Custom Google Spreadsheet ID and link configured at runtime via slash commands.
    - `call_channel_id` / `zvz_channel_id` / `roum_channel_id` / `zvz_role_id` / `roum_role_id`: Channels and roles constraints for organizers and standard command invocation.

## Security
This file acts as a central hub for configuration, making it easier to manage credentials without hardcoding them into the logic scripts. All dynamic configurations are saved in `settings.json` which persists across bot runs.
