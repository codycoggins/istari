# App Improvement ideas

Ideas that have not yet been designed or planned.

## Bugs
- (list here)

## UI
- As the TODO list gets longer, add filters
- Make the size of the right hand TASKS panel adjustable.  User can adjust by dragging the border. Make the default size wider than it is now.
- Keyboard commands: Arrow up gets preveous prompt.  Press repeatedly to scroll back. ctrl-a to beginning, ctrl-e to end. 
- Light and dark mode.

## Backend
- When referring to emails or web pages or file system documents or calendar entries, include a hyperlink in the response. (note: right now when I ask for links it shows them in markdown format, which is a great start but the front end doesn't render markdown.)
- What is current database location- executable and database files
- Add support for command line tools (whitelisted)

## Debugging
- How can Claude do test queries better
- More logging.  Areas of interest:
  - Privacy - log when using a local model
  - call backend endpoints
  - Log usability by both Claude and User

## Data Sources

- Google Drive (use same google auth approach)
- Jira - atlassian acli command line https://developer.atlassian.com/cloud/acli/guides/install-macos/
- Obsidian?  (it is duplicative of file system) - see obsidian CLI, new

## Features affecting data model, backend, frontend
- Add a feature to Istari to have a 'TODO today' area and drag tasks into it
- Add a concept of "projects", a bit like David Allen GTD model. TODOs and knowledge can be associated with projects.  Projects can have urgency/importance like tasks.
- Explore adding positive habits that user wishes to adopt, with tracking.
- Explore adding suggestions for fun activities

## DONE

- The term "Delegate" from Eisenhour matrix -rename to "Contain" for individual contributor?
- Add a refresh button to Istari tasks
- Add a button by tasks that has an icon for context (ma2ybe a question mark?).  It should display relevant info from memories and tools to help the user perform the task/todo 
