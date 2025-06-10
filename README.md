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

This repository contains an enhanced version of aider with improved browser mode that supports all slash commands:

**One-line install:**
```bash
git clone https://github.com/mikeolteanu/aider.git && cd aider && pip install -e .
```

**Features in this custom version:**
- ✅ Enhanced browser mode with full slash command support (`/add`, `/drop`, `/help`, `/tokens`, etc.)
- ✅ Removed analytics and release notes prompts for smoother startup
- ✅ Line-by-line message file processing with `--message-file`
- ✅ Improved file persistence in browser mode
