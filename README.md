Aider lets you pair program with LLMs to start a new project or build on your existing codebase. 

## Features

### [Cloud and local LLMs](https://aider.chat/docs/llms.html)

Aider works best with Claude 3.7 Sonnet, DeepSeek R1 & Chat V3, OpenAI o1, o3-mini & GPT-4o, but can connect to almost any LLM, including local models.


### [Maps your codebase](https://aider.chat/docs/repomap.html)
Aider makes a map of your entire codebase, which helps it work well in larger projects.

### [100+ code languages](https://aider.chat/docs/languages.html)
Aider works with most popular programming languages: python, javascript, rust, ruby, go, cpp, php, html, css, and dozens more.

### [Git integration](https://aider.chat/docs/git.html)

Aider automatically commits changes with sensible commit messages. Use familiar git tools to easily diff, manage and undo AI changes.

### [Use in your IDE](https://aider.chat/docs/usage/watch.html)

Use aider from within your favorite IDE or editor. Ask for changes by adding comments to your code and aider will get to work.

### [Images & web pages](https://aider.chat/docs/usage/images-urls.html)
Add images and web pages to the chat to provide visual context, screenshots, reference docs, etc.

### [Linting & testing](https://aider.chat/docs/usage/lint-test.html)

Automatically lint and test your code every time aider makes changes. Aider can fix problems detected by your linters and test suites.

### [Copy/paste to web chat](https://aider.chat/docs/usage/copypaste.html)

Work with any LLM via its web chat interface. Aider streamlines copy/pasting code context and edits back and forth with a browser.

## Getting Started

### Standard Installation

```bash
python -m pip install aider-install
aider-install

# Change directory into your codebase
cd /to/your/project

# DeepSeek
aider --model deepseek --api-key deepseek=<key>

# Claude 3.7 Sonnet
aider --model sonnet --api-key anthropic=<key>

# o3-mini
aider --model o3-mini --api-key openai=<key>
```

### Custom Installation (Enhanced Browser Mode)

This repository contains an enhanced version of aider with significantly improved browser mode that supports full functionality and user customization:

**One-line install:**
```bash
git clone https://github.com/mikeolteanu/aider.git && cd aider && pip install -e .
```

## 🚀 Custom Features in This Version

### Flask API Mode
- ✅ **REST API server** - Control aider programmatically via HTTP endpoints
- ✅ **Command execution** - Send both slash commands and chat messages via `/command` endpoint
- ✅ **Interactive prompt handling** - API returns prompt details when user input is needed
- ✅ **Single-threaded execution** - Proper command queuing and status management
- ✅ **Complete output capture** - All console output returned in API responses

### Markdown Editor Mode
- ✅ **Specialized markdown editing** - Optimized for technical writing and documentation
- ✅ **Adaptive edit modes** - Automatically chooses between diff and whole-file editing
- ✅ **Flexible file management** - All files editable by default, mark as context-only when needed  
- ✅ **Markdown-optimized prompts** - Best practices for formatting, structure, and syntax
- ✅ **Mixed content workflows** - Edit any files while using others as reference context

### Enhanced Browser Mode
- ✅ **Full slash command support** - All commands work in browser: `/add`, `/drop`, `/help`, `/tokens`, `/run`, `/git`, `/lint`, etc.
- ✅ **Interactive confirmation prompts** - Users can respond to all aider questions directly in the browser interface
- ✅ **Smart prompt preferences** - Configure which prompts to auto-approve, auto-deny, or always ask about
- ✅ **Command output display** - All command results (like `/run ls`) now appear in the browser, not just console
- ✅ **Session cost tracking** - Real-time cost display in collapsed session info
- ✅ **Collapsible session info** - Clean interface with expandable technical details
- ✅ **Settings management** - Easy-to-use UI for configuring browser behavior

### Command Output Improvements
- ✅ **`/run` command results** now display immediately in browser interface
- ✅ **`/git diff` output** properly captured and shown in browser
- ✅ **Shell command suggestions** from LLM show output in browser before adding to chat
- ✅ **Exit codes and error handling** clearly displayed for all commands

### User Experience Enhancements  
- ✅ **Removed redundant messaging** - No more "How can I help you?" and startup noise
- ✅ **Smart session display** - Shows version and current cost on one clean line
- ✅ **Tabbed sidebar** - Organized interface with Main and Settings tabs
- ✅ **Visual confirmation prompts** - Clear buttons for Yes/No/All/Skip All/Don't Ask Again

### Configuration System
- ✅ **Browser config file** - `~/.aider_browser_config.json` for persistent settings
- ✅ **Granular prompt control** - Set preferences for 20+ different confirmation types:
  - **File Operations**: Create files, add to chat, edit files not in chat
  - **Command Execution**: Shell commands, output inclusion, security prompts  
  - **Installation**: Package installs, tool setup, OAuth login
  - **Error Handling**: Lint fixes, test fixes, context window issues
  - **URLs & Web**: URL detection, documentation links
  - **Repository**: Git repo creation, .gitignore management
  - **Analytics**: Data collection preferences
- ✅ **Smart defaults** - Optimized for smooth development:
  - **Auto-approve**: File creation, lint fixes, package installs, command output inclusion
  - **Always ask**: Shell commands (security), file edits outside chat (control), analytics (privacy)
  - **Auto-deny**: URL additions, documentation popups (reduces noise)
- ✅ **Category organization** - Settings grouped logically with helpful descriptions

### Security & Control
- ✅ **Preserved security model** - Shell commands still require explicit confirmation when configured to ask
- ✅ **User choice** - Full control over automation vs. manual approval for each prompt type
- ✅ **Extensible design** - Easy to add new prompt types and browser settings

### Legacy Features
- ✅ **Line-by-line message file processing** with `--message-file`
- ✅ **Improved file persistence** in browser mode
- ✅ **Removed analytics and release notes prompts** for smoother startup

### Usage Examples

**API mode:**
```bash
# Start API server
aider --api

# Send commands via HTTP (from another terminal or script)
curl -X POST http://127.0.0.1:5000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"/add src/main.py"}'

curl -X POST http://127.0.0.1:5000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"add error handling to the login function"}'

# Check server status
curl http://127.0.0.1:5000/status
```

**Markdown editor mode:**
```bash
# Start markdown editor mode
aider --markdown-editor

# Add all files (all editable by default)
/add README.md docs/guide.md CONTRIBUTING.md src/main.py tests/test_main.py

# Mark code files as context-only for reference  
/context-only src/main.py tests/test_main.py

# Now edit files with intelligent mode selection:
# "Replace all instances of 'setup.py' with 'pyproject.toml'" → Uses diff mode
# "Reformat this entire document with better structure" → Uses whole file mode
```

**Browser mode with custom config:**
```bash
# Start browser mode
aider --browser

# Settings are automatically loaded from ~/.aider_browser_config.json
# Configure preferences in Settings tab of browser interface
```

**Combined modes:**
```bash
# Use markdown editor mode with API access
aider --api --markdown-editor

# Use markdown editor mode in browser
aider --browser --markdown-editor

# API mode with specific model
aider --api --model claude-3-5-sonnet-20241022

# All modes support the full range of aider features
aider --api --markdown-editor --auto-commits --model sonnet
```

**Example configuration scenarios:**
- **Development workflow**: Auto-approve lint fixes, test fixes, and package installs
- **Security-focused**: Ask for all commands, auto-deny URL additions  
- **Streamlined**: Auto-approve file creation and repo setup, ask for everything else

This enhanced version transforms aider's browser mode from a limited interface into a full-featured development environment with smart automation and complete user control.

## 📚 Additional Documentation

- **[Markdown Editor Mode Guide](markdown_editor_mode.md)** - Complete guide to the new markdown editing features
- **[API Mode Documentation](api_implementation_docs.md)** - Technical details on the Flask API implementation  
- **[OpenAPI Specification](openapi.yaml)** - REST API documentation for programmatic access
