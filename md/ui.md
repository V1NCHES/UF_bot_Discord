# User Interface Components (`ui.py`)

This module manages all the interactive elements of the Discord bot using the `discord.ui` framework.

## Key Components
- **Views (Buttons & Menus)**:
    - `StartCallView`: Initial setup buttons for creating a new event.
    - `CallRoleView`: The main interface for events where users can click buttons to sign up for specific roles (limited safely to 21 slot buttons to fit Discord's 25-component limit alongside organizer buttons).
    - `OrganizerMenuView`: An control panel view for organizers, containing pauses, link updates, player assignments, slot edits, and call finishing toggles.
    - `RegearPersistentView`: Persistent interface for officers to moderate regear applications. Features three buttons: `✅ Одобрить`, `❌ Отклонить`, and `📦 Выдано`.
        - *Dynamic Button Removal*: When an officer clicks **Approved**, the view is updated to remove the "Одобрить" and "Отклонить" buttons, leaving only the "Выдано" button for final payout tracking. When **Rejected** or **Issued**, all buttons are completely removed from the panel.
- **Modals (Forms)**:
    - `CreateCallModal`: A pop-up form used by organizers to set the event description, link, duration, and slots.
    - `SaveTemplateModal`: A modal form prompting organizers to enter a custom name when saving their call setup as a template.
    - `RegearRejectModal`: A dynamic form launched when clicking the `❌ Отклонить` button, prompting the officer to enter a rejection reason.
- **Content Generation**:
    - `generate_combined_call_message`: A unified function that formats a single plain-text message per destination. It displays the ping role at the start, followed by scheduling metadata (times, organizers, IDs), followed by the complete group roster (`Состав группы`).

## Logic
- Handles button interactions (sign-up, sign-off) and prevents crashes by capping rendering views to 25 items.
- Manages state for active calls within the UI components.
- Updates messages dynamically when users interact with the UI, cleanly synchronizing edits across main channel posts and corresponding threads.
