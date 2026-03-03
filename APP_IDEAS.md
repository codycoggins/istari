# App Improvement ideas

Ideas that have not yet been designed or planned.

# Bugs
gmail integration broke after the refactor moving gmail_token.json to secrets/
Gmail isn't connected yet. Run `python scripts/setup_gmail.py` to link your Gmail account."

## UI
- Add a button by tasks that has an icon for context (maybe a question mark?).  It should display relevant info from memories and tools to help the user perform the task/todo 
- As the TODO list gets longer, add filters
- Make the size of the right hand TASKS panel adjustable.  User can adjust by dragging the border. Make the default size wider than it is now.
- Light and dark mode.
- Add markdown support

## Backend
- When referring to emails or web pages or file system documents or calendar entries, include a hyperlink in the response. (note: right now when I ask for links it shows them in markdown format, which is a great start but the front end doesn't render markdown.)
- What is current database location- executable and database files
- Add support for command line tools (whitelisted)
- More logging.  Areas of interest:
  - Privacy - log when using a local model
  - call backend endpoints

## Data Sources

- Google Drive (use same google auth approach
- Jira - atlassian acli command line https://developer.atlassian.com/cloud/acli/guides/install-macos/
- Obsidian?  (it is duplicative of file system) - see obsidian CLI, new

## Data Model

- Add a concept of "projects", a bit like David Allen GTD model. TODOs and knowledge can be associated with projects.  Projects can have urgency/importance like tasks.
- Explore adding positive habits that user wishes to adopt, with tracking.
- Explore adding suggestions for fun activities
