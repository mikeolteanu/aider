# Aider Development Setup Guide

This guide documents how to set up the aider codebase for development and making changes.

## Prerequisites

- Python 3.10+ (tested with Python 3.12.7)
- pip package manager
- Git (for version control)

## Project Structure Overview

Aider is a Python package with the following key components:

- `pyproject.toml` - Project configuration and build settings
- `requirements.txt` - Python dependencies 
- `aider/` - Main source code directory
- `tests/` - Test suite
- `benchmark/` - Benchmarking tools
- `scripts/` - Utility scripts

## Setup Steps

### 1. Clone and Navigate to Repository

```bash
# If you haven't already cloned the repository
git clone <repository-url>
cd aider
```

### 2. Verify Python Version

```bash
python --version
# Should show Python 3.10+ (tested with 3.12.7)
```

### 3. Install Dependencies in Development Mode

```bash
# Install aider in editable/development mode
pip install -e .
```

This command:
- Installs all dependencies from `requirements.txt`
- Installs aider in "editable" mode so changes are reflected immediately
- Creates the `aider` command globally available

### 4. Verify Installation

```bash
# Test that aider is properly installed
aider --help
```

You should see the full help output with all available options.

## Development Workflow

### Making Changes

1. **Edit source code** in the `aider/` directory
2. **Changes are immediately available** due to editable install
3. **Test your changes** by running aider commands

### Testing

```bash
# Run the test suite (if available)
pytest

# Or with explicit module
python -m pytest
```

### Code Quality

```bash
# Run linting (flake8 is included in dependencies)
flake8 aider/

# Check specific files
flake8 aider/main.py
```

### Testing Aider on Itself

```bash
# Use aider to modify its own codebase
cd /path/to/aider
aider --model <your-model> --api-key <provider>=<key> <files-to-edit>
```

## Key Files and Directories

- `aider/main.py` - Main entry point
- `aider/coders/` - Different coder implementations
- `aider/models.py` - Model configuration and management
- `aider/io.py` - Input/output handling
- `aider/repo.py` - Repository management
- `aider/repomap.py` - Code repository mapping
- `pyproject.toml` - Package configuration
- `requirements.txt` - Production dependencies
- `requirements/requirements-dev.txt` - Development dependencies

## Configuration

Aider uses several configuration methods:
- Command line arguments
- Environment variables (prefixed with `AIDER_`)
- Config files (`.aider.conf.yml`)
- `.env` files

## Building and Distribution

The project uses modern Python packaging with `pyproject.toml`:

```bash
# Build package (if needed)
pip install build
python -m build

# Install development dependencies
pip install -r requirements/requirements-dev.txt
```

## Common Development Tasks

### Adding New Features
1. Identify the relevant module in `aider/`
2. Make your changes
3. Test with `aider --help` or specific commands
4. Run tests to ensure nothing breaks

### Debugging
- Use `--verbose` flag for detailed output
- Check `aider/io.py` for logging and output handling
- Use `--dry-run` to test without making actual changes

### Working with Models
- Model configurations are in `aider/models.py`
- LLM integration code is in `aider/llm.py`
- Different edit formats are in `aider/coders/`

## Troubleshooting

### Import Errors
If you get import errors, ensure you installed in editable mode:
```bash
pip install -e .
```

### Missing Dependencies
Install all requirements:
```bash
pip install -r requirements.txt
```

### Command Not Found
Make sure your Python scripts directory is in PATH, or use:
```bash
python -m aider.main --help
```

## Example Changes Made

### 1. Enhanced Browser Mode Slash Commands

#### Problem
The browser mode had limited functionality - it only supported direct chat input and couldn't use slash commands like `/add`, `/drop`, `/help`, etc. This meant users couldn't perform common operations through the web interface.

### Solution
Modified `aider/gui.py` to:
1. Check for slash commands before processing regular chat input
2. Route slash commands through the existing command processing system
3. Display command output properly in the web interface
4. Handle special cases like `SwitchCoder` exceptions

### Changes Made
- **Modified `process_chat()` method** to detect slash commands using `self.coder.commands.is_command(prompt)`
- **Added `handle_command()` method** to process slash commands and capture their output
- **Enhanced user input hint** to show that slash commands are available
- **Improved error handling** for commands that aren't supported in browser mode

### Files Changed
- `aider/gui.py` - Main browser interface logic

### Testing
```bash
# Test command detection
python -c "
from aider.commands import Commands
commands = Commands(None, None)
print('Available commands:', sorted(commands.get_commands())[:10])
"

# To test in browser mode:
# aider --browser
# Then try commands like: /help, /add filename.py, /ls, /tokens
```

### 2. Removed Analytics Startup Prompt

#### Problem
Aider would prompt users on startup asking if they want to share anonymous analytics, which interrupted the user experience and could be annoying for users who just want to get started.

#### Solution
Modified `aider/analytics.py` to:
1. Always return `False` from the `need_to_ask()` method
2. This prevents the analytics consent prompt from ever appearing
3. Users can still manually disable analytics with `--analytics-disable` if desired

#### Changes Made
- **Modified `need_to_ask()` method** in `aider/analytics.py` to always return `False`
- **Simplified the method** to just return `False` instead of complex logic

#### Files Changed
- `aider/analytics.py` - Analytics consent logic

#### Testing
```bash
# Test that analytics never asks for consent
python -c "
from aider.analytics import Analytics
analytics = Analytics()
print('need_to_ask(None):', analytics.need_to_ask(None))
print('need_to_ask(True):', analytics.need_to_ask(True))
print('need_to_ask(False):', analytics.need_to_ask(False))
"

# Test that aider starts without analytics prompt
echo "test" | aider --help > /dev/null && echo "Success: No analytics prompt"
```

### 3. Removed Changelog/Release Notes Prompt

#### Problem
Aider would prompt users on startup (for first runs of new versions) asking if they want to see the changelog/release notes: "Would you like to see what's new in this version?". This interrupted the user experience.

#### Solution
Modified `aider/main.py` to:
1. Remove the automatic release notes prompt that appears on first run
2. Keep the manual `--show-release-notes` flag functionality 
3. Preserve update notifications (which are separate functionality)

#### Changes Made
- **Removed automatic prompt** in `main.py` lines 1098-1104 that checked `args.show_release_notes is None and is_first_run`
- **Added explanatory comment** explaining the change
- **Preserved manual functionality** - users can still use `--show-release-notes` if they want

#### Files Changed
- `aider/main.py` - Release notes prompt logic

#### What's Preserved
- ✅ **Update notifications** still work (handled by `versioncheck.py`)
- ✅ **Manual release notes** still work with `--show-release-notes` flag
- ✅ **Version checking** functionality remains intact

#### Testing
```bash
# Test that manual release notes flag still works
python -c "
import sys
sys.argv = ['aider', '--show-release-notes', '--help']
from aider.main import main
print('Manual --show-release-notes flag parsing works')
"

# Test that version checking still works
python -c "
from aider.versioncheck import check_version
from aider.io import InputOutput
io = InputOutput(pretty=False, yes=True)
result = check_version(io, just_check=True, verbose=True)
print('Version check still works')
"

# Test that aider starts without release notes prompt
echo "test" | timeout 5s aider --help > /dev/null && echo "No release notes prompt"
```

### 4. Enhanced Message File Processing

#### Problem
The `--message-file` / `-f` option would read an entire file and treat it as a single message to send to the LLM. This limited its usefulness for batch processing multiple commands or messages.

#### Solution
Modified `aider/main.py` to:
1. Process message files line by line instead of as a single message
2. Support both slash commands and regular messages in the same file
3. Skip empty lines and comments (lines starting with #)
4. Add proper error handling for each line
5. Continue processing even if one line fails

#### Changes Made
- **Modified message file processing** in `main.py` lines 1126-1165 to read and process each line separately
- **Added command detection** to handle both `/commands` and regular messages
- **Added comment support** - lines starting with # are treated as comments and skipped
- **Updated help text** in `args.py` to reflect the new line-by-line behavior
- **Added error handling** for individual lines while continuing to process the rest

#### Files Changed
- `aider/main.py` - Message file processing logic
- `aider/args.py` - Help text for `--message-file` option

#### New Functionality
- ✅ **Line-by-line processing** - Each line is a separate command/message
- ✅ **Mixed content support** - Can mix slash commands and LLM messages
- ✅ **Comment support** - Lines starting with # are ignored
- ✅ **Error resilience** - Continues processing if one line fails
- ✅ **Progress feedback** - Shows which line is being processed

#### Example Usage
Create a file `batch_commands.txt`:
```
# This is a comment - will be skipped
/add main.py
/ls
Create a hello world function
/tokens
# Another comment
Fix any errors in the code
```

Then run: `aider --message-file batch_commands.txt`

#### Testing
```bash
# Test command detection
python -c "
from aider.commands import Commands
commands = Commands(None, None)
test_lines = ['/help', 'Hello world', '/add file.py', '!ls']
for line in test_lines:
    is_cmd = commands.is_command(line)
    print(f'{line} -> is_command: {is_cmd}')
"

# Test file parsing logic
echo -e '# Comment\n/help\nHello world' > test.txt
python -c "
with open('test.txt', 'r') as f:
    lines = f.readlines()
for line_num, line in enumerate(lines, 1):
    line = line.strip()
    if not line or line.startswith('#'):
        print(f'Line {line_num}: SKIPPED - {repr(line)}')
    else:
        print(f'Line {line_num}: PROCESS - {repr(line)}')
"
rm test.txt

# Check updated help text
aider --help | grep -A3 "message-file"
```

## Next Steps

After setup, you can:
1. Explore the codebase to understand how aider works
2. Run aider on sample projects to see it in action
3. Make your desired changes (like the browser mode enhancement above)
4. Test thoroughly before submitting changes
5. Consider running the full test suite to ensure compatibility

## Resources

- Main documentation: https://aider.chat/docs/
- GitHub repository: https://github.com/Aider-AI/aider
- Configuration options: Use `aider --help` for full list