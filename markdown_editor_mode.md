# Markdown Editor Mode

Aider's Markdown Editor Mode is a specialized editing mode optimized for working with markdown files. It provides intelligent choice between diff-based and whole-file editing, along with sophisticated file management for mixed content types.

## Features

### 🎯 **Adaptive Edit Mode Selection**
- **Diff Mode**: For targeted changes like word replacements, typo fixes, small additions
- **Whole File Mode**: For major restructuring, reformatting, or extensive changes (>50% content)
- **Automatic Selection**: The LLM intelligently chooses the appropriate mode based on change scope

### 📝 **Markdown-Optimized Prompting**
- Specialized prompts for technical writing and documentation
- Best practices for markdown formatting and structure  
- Maintains consistent heading hierarchy and formatting
- Proper handling of code blocks, tables, and links

### 📁 **Smart File Management**
- **Editable Files**: All files are editable by default (can be modified)
- **Context Files**: Read-only reference files for background information
- **User Control**: Files are only read-only when explicitly marked that way
- **Manual Classification**: Use commands to reclassify files as needed

## Usage

### Starting Markdown Editor Mode

```bash
# Launch aider in markdown editor mode
aider --markdown-editor

# Or specify the edit format
aider --edit-format markdown-editor
```

### File Management Commands

```bash
# Show current file classifications
/editable          # List editable files
/context-only       # List context-only files

# Mark files as editable (can be modified)
/editable file1.md file2.md

# Mark files as context-only (read-only reference)
/context-only reference.md background.txt

# Regular file operations still work
/add newfile.md     # Add as editable (if .md extension)
/read-only ref.py   # Add as context-only
```

## Example Workflows

### 1. Targeted Word Replacement
```
User: "Replace all instances of 'Bob' with 'Michael' in the README.md"

AI Response: Uses DIFF MODE for precise word replacements:
```diff
--- README.md
+++ README.md
@@ ... @@
-## About Bob
+## About Michael
@@ ... @@
-Contact Bob at bob@example.com
+Contact Michael at michael@example.com
```

### 2. Document Restructuring
```
User: "Completely reformat this markdown file with better structure, add a table of contents, and reorganize sections"

AI Response: Uses WHOLE FILE MODE for major restructuring:
```markdown
# Project Documentation

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Installation](#installation)
...

## Overview
Restructured content with improved organization...
```

### 3. Mixed Content Workflow
```bash
# Set up files for documentation project
aider --markdown-editor

# Add all files (all editable by default)
/add README.md CONTRIBUTING.md docs/guide.md src/main.py tests/test_main.py

# Mark code files as context-only for reference
/context-only src/main.py tests/test_main.py

# Now you can edit markdown while referencing code
"Update the installation instructions in README.md based on the requirements in main.py"
```

## Technical Details

### Mode Selection Logic
The LLM automatically chooses between diff and whole-file mode based on:

- **Change Scope**: How much of the file is being modified
- **Change Type**: Structural vs. content changes
- **Efficiency**: Diff size vs. whole file size
- **Reliability**: Risk of diff match failures

### File Type Handling
- **All Extensions**: Any file type can be added and edited
- **Default Behavior**: All files → editable (can be modified)
- **Read-Only Override**: Use `/context-only` to mark files as read-only reference
- **Manual Classification**: Use `/editable` and `/context-only` to change file roles

### Diff Format
Uses unified diff format similar to `diff -U0`:
```diff
--- filename.md
+++ filename.md  
@@ line_numbers @@
-old content
+new content
```

### Whole File Format
Complete file replacement with filename and code fences:
```
filename.md
```
# Complete file content
New markdown content here...
```

## Best Practices

### 1. File Organization
- All files are editable by default for maximum flexibility
- Mark files as `/context-only` when you want them for reference only
- Regularly review file classifications with `/editable` and `/context-only`

### 2. Prompt Design
- Be specific about the scope of changes needed
- Mention if you want targeted edits vs. complete restructuring
- Reference specific sections or elements to modify

### 3. Change Management
- For large documents, consider breaking into smaller files
- Use meaningful commit messages for tracking changes
- Review diffs before accepting major restructuring

## Integration with Other Modes

Markdown Editor Mode can be combined with other aider features:

```bash
# Use with API mode
aider --api --edit-format markdown-editor

# Use with specific models
aider --markdown-editor --model claude-3-5-sonnet-20241022

# Use with git features
aider --markdown-editor --auto-commits
```

## Troubleshooting

### Common Issues

**Diff Fails to Apply**
- File content may have changed since LLM saw it
- Try asking for whole file mode: "Please rewrite the entire file"

**Wrong Mode Selected**
- Be more specific about change scope in your prompt
- Explicitly request: "Use diff format" or "Rewrite the entire file"

**File Classification Issues**
- Check current classifications: `/editable` and `/context-only`
- Manually reclassify files as needed

### Error Messages

- `"Cannot edit X: file is read-only or not marked as editable"` → Use `/editable filename`
- `"This command is only available in markdown editor mode"` → Start with `--markdown-editor`
- `"Hunk does not match file content"` → Ask for whole file mode instead

## Examples

See the examples in the markdown editor prompts for detailed usage patterns and expected outputs.