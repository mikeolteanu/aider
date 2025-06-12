from pathlib import Path
from typing import Set

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .markdown_editor_prompts import MarkdownEditorPrompts
from .editblock_coder import find_original_update_blocks, do_replace


class MarkdownEditorCoder(Coder):
    """A coder optimized for editing markdown files with adaptive diff/whole-file mode selection."""

    edit_format = "markdown-editor"
    gpt_prompts = MarkdownEditorPrompts()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track which files are editable vs read-only context
        self.editable_files: Set[str] = set()
        self.context_files: Set[str] = set()
        self._classify_files()

    def _classify_files(self):
        """Classify files as editable or context based on user specification."""
        # All files are editable by default
        for fname in self.abs_fnames or []:
            self.editable_files.add(fname)
        
        # Read-only files are always context
        for fname in self.abs_read_only_fnames or []:
            self.context_files.add(fname)
            self.editable_files.discard(fname)

    def add_rel_fname(self, fname, mode='editable'):
        """Add a file with specified mode (editable or context)."""
        result = super().add_rel_fname(fname)
        abs_fname = self.abs_root_path(fname)
        
        if mode == 'context':
            self.context_files.add(abs_fname)
            self.editable_files.discard(abs_fname)
        else:
            # All files are editable by default
            self.editable_files.add(abs_fname)
            self.context_files.discard(abs_fname)
        
        return result

    def _add_editable_file_if_not_context(self, abs_fname):
        """Helper to add file as editable if not explicitly marked as context"""
        if abs_fname not in self.context_files:
            self.editable_files.add(abs_fname)

    def drop_rel_fname(self, fname):
        """Remove a file from tracking."""
        result = super().drop_rel_fname(fname)
        abs_fname = self.abs_root_path(fname)
        self.editable_files.discard(abs_fname)
        self.context_files.discard(abs_fname)
        return result

    def render_incremental_response(self, final):
        """Render incremental response showing edits as they come in."""
        return self.get_multi_response_content_in_progress()

    def get_edits(self, mode="update"):
        """Parse the LLM response to extract and apply edits."""
        content = self.partial_response_content
        
        # Check if content contains search-and-replace blocks
        if "<<<<<<< SEARCH" in content and ">>>>>>> REPLACE" in content:
            # Parse search-and-replace blocks
            edits = list(
                find_original_update_blocks(
                    content,
                    self.fence,
                    self.get_inchat_relative_files(),
                )
            )
            # Filter out shell commands
            self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
            edits = [edit for edit in edits if edit[0] is not None]
        else:
            # Try whole file format parsing
            edits = self._parse_whole_file_format(content, mode)
        
        # Filter edits based on file classification
        filtered_edits = []
        for edit in edits:
            if len(edit) == 3:  # search-and-replace format (path, original, updated)
                path, original, updated = edit
                full_path = self.abs_root_path(path)
                
                # Check if file is explicitly marked as context-only
                if full_path in self.context_files:
                    self.io.tool_error(f"Cannot edit {path}: file is marked as context-only")
                    continue
                
                # Add new files to editable set automatically
                if full_path not in self.editable_files:
                    self.editable_files.add(full_path)
                
                filtered_edits.append(edit)
            elif len(edit) == 2:  # whole file format (path, content)
                path, content = edit
                full_path = self.abs_root_path(path)
                
                # Check if file is explicitly marked as context-only
                if full_path in self.context_files:
                    self.io.tool_error(f"Cannot edit {path}: file is marked as context-only")
                    continue
                
                # Add new files to editable set automatically
                if full_path not in self.editable_files:
                    self.editable_files.add(full_path)
                
                filtered_edits.append(edit)
        
        return filtered_edits
    
    def _parse_whole_file_format(self, content, mode):
        """Parse whole file format using WholeFileCoder logic: filename.ext followed by ``` content ```"""
        edits = []
        chat_files = self.get_inchat_relative_files()
        lines = content.splitlines(keepends=True)
        
        saw_fname = None
        fname = None
        fname_source = None
        new_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith(self.fence[0]) or line.startswith(self.fence[1]):
                if fname is not None:
                    # ending an existing block
                    new_content = "".join(new_lines)
                    edits.append((fname, new_content))
                    fname = None
                    fname_source = None
                    new_lines = []
                    continue

                # fname==None ... starting a new block
                if i > 0:
                    fname_source = "block"
                    fname = lines[i - 1].strip()
                    fname = fname.strip("*")  # handle **filename.py**
                    fname = fname.rstrip(":")
                    fname = fname.strip("`")
                    fname = fname.lstrip("#")
                    fname = fname.strip()

                    # Issue #1232
                    if len(fname) > 250:
                        fname = ""

                    # Did gpt prepend a bogus dir? It especially likes to
                    # include the path/to prefix from the one-shot example in
                    # the prompt.
                    if fname and fname not in chat_files and Path(fname).name in chat_files:
                        fname = Path(fname).name
                        
                if not fname:  # blank line? or ``` was on first line i==0
                    if saw_fname:
                        fname = saw_fname
                        fname_source = "saw"
                    elif len(chat_files) == 1:
                        fname = chat_files[0]
                        fname_source = "chat"
                    else:
                        # Skip this block if we can't determine filename
                        continue

            elif fname is not None:
                new_lines.append(line)
            else:
                for word in line.strip().split():
                    word = word.rstrip(".:,;!")
                    for chat_file in chat_files:
                        quoted_chat_file = f"`{chat_file}`"
                        if word == quoted_chat_file:
                            saw_fname = chat_file

        # Handle final block
        if fname is not None and new_lines:
            new_content = "".join(new_lines)
            edits.append((fname, new_content))

        return edits
    
    def apply_edits(self, edits, dry_run=False):
        """Apply both search-and-replace and whole file edits"""
        applied_files = []
        failed_edits = []
        
        for edit in edits:
            if len(edit) == 3:  # search-and-replace format
                path, original, updated = edit
                full_path = self.abs_root_path(path)
                
                if Path(full_path).exists():
                    content = self.io.read_text(full_path)
                    new_content = do_replace(full_path, content, original, updated, self.fence)
                    
                    if new_content:
                        if not dry_run:
                            self.io.write_text(full_path, new_content)
                        applied_files.append(path)
                    else:
                        failed_edits.append(edit)
                else:
                    failed_edits.append(edit)
                    
            elif len(edit) == 2:  # whole file format
                path, content = edit
                full_path = self.abs_root_path(path)
                
                if not dry_run:
                    try:
                        self.io.write_text(full_path, content)
                        applied_files.append(path)
                    except Exception as e:
                        self.io.tool_error(f"Failed to write {path}: {str(e)}")
                else:
                    applied_files.append(path)
        
        # Handle failed search-and-replace edits
        if failed_edits and not dry_run:
            blocks = "block" if len(failed_edits) == 1 else "blocks"
            res = f"# {len(failed_edits)} SEARCH/REPLACE {blocks} failed to match!\n"
            for edit in failed_edits:
                path, original, updated = edit
                res += f"""
## SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines in {path}
<<<<<<< SEARCH
{original}=======
{updated}>>>>>>> REPLACE

"""
            res += (
                "The SEARCH section must exactly match an existing block of lines including all white"
                " space, comments, indentation, docstrings, etc\n"
            )
            raise ValueError(res)
        
        return applied_files





    def _ensure_file_is_tracked(self, abs_fname: str):
        """Ensure file is properly tracked in our collections"""
        # Add to main files list if not already there and not read-only
        if abs_fname not in self.abs_read_only_fnames:
            if abs_fname not in self.abs_fnames:
                self.abs_fnames.add(abs_fname)
            
            # Add to editable files if not in context files
            if abs_fname not in self.context_files:
                self.editable_files.add(abs_fname)


    def get_context_from_history(self, history):
        """Enhanced context including file classification information."""
        context = super().get_context_from_history(history)
        
        if self.editable_files or self.context_files:
            context += "\n\n# File Classification:\n"
            
            if self.editable_files:
                context += "## Editable Files (can be modified):\n"
                for fname in sorted(self.editable_files):
                    rel_path = self.get_rel_fname(fname)
                    context += f"- {rel_path}\n"
            
            if self.context_files:
                context += "## Context Files (read-only reference):\n"
                for fname in sorted(self.context_files):
                    rel_path = self.get_rel_fname(fname)
                    context += f"- {rel_path}\n"
        
        return context

    def debug_file_classifications(self):
        """Debug method to print current file classifications"""
        print("=== FILE CLASSIFICATIONS DEBUG ===")
        print(f"abs_fnames: {self.abs_fnames}")
        print(f"abs_read_only_fnames: {self.abs_read_only_fnames}")
        print(f"editable_files: {self.editable_files}")
        print(f"context_files: {self.context_files}")
        print("====================================")