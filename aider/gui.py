#!/usr/bin/env python

import json
import os
import random
import re
import sys

import streamlit as st

from aider import urls
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.main import main as cli_main
from aider.scrape import Scraper, has_playwright


class BrowserConfig:
    """Manages browser-specific configuration for prompt preferences"""
    
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.expanduser("~/.aider_browser_config.json")
        self.config = self.load_config()
    
    def load_config(self):
        """Load config from file, create default if not found"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load browser config: {e}")
        
        # Return default config
        return self.get_default_config()
    
    def save_config(self):
        """Save current config to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving browser config: {e}")
            return False
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            "version": "1.0",
            "description": "Aider browser mode configuration file - Optimized defaults for smooth development workflow",
            "prompt_preferences": {
                "file_operations": {
                    "create_new_file": "always_yes",
                    "add_file_to_chat": "always_yes", 
                    "edit_file_not_in_chat": "ask",
                    "create_from_pattern": "always_yes"
                },
                "command_execution": {
                    "run_shell_commands": "ask",
                    "add_command_output": "always_yes",
                    "add_run_output": "always_yes"
                },
                "installation": {
                    "pip_install": "always_yes",
                    "install_playwright": "always_yes",
                    "openrouter_login": "ask"
                },
                "error_handling": {
                    "fix_lint_errors": "always_yes",
                    "fix_test_errors": "always_yes", 
                    "context_window_exceeded": "ask"
                },
                "urls_and_web": {
                    "add_url_to_chat": "always_no",
                    "open_documentation_url": "always_no"
                },
                "repository": {
                    "create_git_repo": "always_yes",
                    "add_to_gitignore": "always_yes"
                },
                "analytics": {
                    "analytics_opt_in": "ask"
                },
                "architect_mode": {
                    "execute_plan": "ask"
                }
            },
            "prompt_patterns": {
                "Create new file?": "create_new_file",
                "Add file to the chat?": "add_file_to_chat",
                "Allow edits to file that has not been added to the chat?": "edit_file_not_in_chat",
                "No files matched .* Do you want to create .*": "create_from_pattern",
                "Run shell command.*": "run_shell_commands",
                "Add command output to the chat?": "add_command_output",
                "Add .* tokens of command output to the chat?": "add_run_output",
                "Run pip install?": "pip_install",
                "Install playwright?": "install_playwright",
                "Login to OpenRouter or create a free account?": "openrouter_login",
                "Attempt to fix lint errors?": "fix_lint_errors",
                "Fix lint errors in .*": "fix_lint_errors",
                "Attempt to fix test errors?": "fix_test_errors",
                "Try to proceed anyway?": "context_window_exceeded",
                "Add URL to the chat?": "add_url_to_chat",
                "Open .* URL .* for more info?": "open_documentation_url",
                "No git repo found, create one to track aider's changes .*": "create_git_repo",
                "Add .* to .gitignore .*": "add_to_gitignore",
                "Allow collection of anonymous analytics to help improve aider?": "analytics_opt_in",
                "Edit the files?": "execute_plan"
            },
            "ui_settings": {
                "theme": "auto",
                "show_session_cost": True,
                "collapsed_announcements": True,
                "auto_load_recent_history": False
            }
        }
    
    def get_prompt_preference(self, question):
        """Get preference for a specific prompt question"""
        # Find matching pattern
        for pattern, preference_key in self.config.get("prompt_patterns", {}).items():
            if re.search(pattern, question, re.IGNORECASE):
                # Find the preference value by looking through categories
                for category in self.config.get("prompt_preferences", {}).values():
                    if preference_key in category:
                        return category[preference_key]
        
        # Default to ask if no pattern matches
        return "ask"
    
    def update_preference(self, preference_key, value):
        """Update a specific preference"""
        # Find and update the preference in the appropriate category
        for category in self.config["prompt_preferences"].values():
            if preference_key in category:
                category[preference_key] = value
                return True
        return False
    
    def get_all_preferences(self):
        """Get all preferences organized by category"""
        return self.config.get("prompt_preferences", {})


class BrowserIO(InputOutput):
    lines = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gui_state = None
        self.browser_config = BrowserConfig()
        self.pending_operation = None  # Store operation to complete after confirmation

    def tool_output(self, *messages, log_only=False):
        if not log_only and messages:
            self.lines.append(" ".join(str(msg) for msg in messages))
        super().tool_output(*messages, log_only=log_only)

    def tool_error(self, msg):
        self.lines.append(msg)
        super().tool_error(msg)

    def tool_warning(self, msg):
        self.lines.append(msg)
        super().tool_warning(msg)

    def get_captured_lines(self):
        lines = self.lines
        self.lines = []
        return lines

    def confirm_ask(
        self,
        question,
        default="y",
        subject=None,
        explicit_yes_required=False,
        group=None,
        allow_never=False,
    ):
        """Override confirm_ask to handle interactive prompts in browser mode"""
        self.num_user_asks += 1

        # Ring the bell if needed
        self.ring_bell()

        question_id = (question, subject)

        if question_id in self.never_prompts:
            return False

        # Check browser config for this prompt type
        preference = self.browser_config.get_prompt_preference(question)
        if preference == "always_yes":
            return True
        elif preference == "always_no":
            return False
        # If preference is "ask", continue with normal prompt flow

        # Check if we already have a response waiting
        if self.gui_state and self.gui_state.confirmation_response:
            response = self.gui_state.confirmation_response
            self.gui_state.confirmation_response = None  # Clear the response
            
            # Process the response like the original method
            if response.lower().startswith("y"):
                return True
            elif response.lower().startswith("n"):
                return False
            elif response.lower().startswith("a"):
                if group:
                    group.preference = True
                return True
            elif response.lower().startswith("s"):
                if group:
                    group.preference = False
                return False
            elif response.lower().startswith("d"):
                self.never_prompts.add(question_id)
                return False
            else:
                # Default fallback
                return default.lower().startswith("y")

        if group and not group.show_group:
            group = None
        if group:
            allow_never = True

        valid_responses = ["yes", "no", "skip", "all"]
        options = " (Y)es/(N)o"
        if group:
            if not explicit_yes_required:
                options += "/(A)ll"
            options += "/(S)kip all"
        if allow_never:
            options += "/(D)on't ask again"
            valid_responses.append("don't")

        if default.lower().startswith("y"):
            question += options + " [Yes]: "
        elif default.lower().startswith("n"):
            question += options + " [No]: "
        else:
            question += options + f" [{default}]: "

        # Store the prompt details for the browser UI to display
        prompt_data = {
            "question": question,
            "subject": subject,
            "default": default,
            "explicit_yes_required": explicit_yes_required,
            "group": group,
            "allow_never": allow_never,
            "valid_responses": valid_responses
        }
        
        if self.gui_state:
            self.gui_state.pending_confirmation = prompt_data
            
            # For the special case of "Add tokens to chat", store the context needed
            # to complete the operation
            if "tokens of command output to the chat" in question:
                # This is likely from the /run command, store additional context
                # We need to extract this from the call stack, but for now let's use a simpler approach
                prompt_data["is_add_to_chat"] = True
        
        # Signal that we need user input by raising an exception
        # This will be caught by the browser interface
        raise BrowserPromptException(prompt_data)


class BrowserPromptException(Exception):
    """Exception raised when browser needs to prompt user for input"""
    def __init__(self, prompt_data, completion_callback=None):
        self.prompt_data = prompt_data
        self.completion_callback = completion_callback
        super().__init__("Browser prompt required")


def search(text=None):
    results = []
    for root, _, files in os.walk("aider"):
        for file in files:
            path = os.path.join(root, file)
            if not text or text in path:
                results.append(path)
    # dump(results)

    return results


# Keep state as a resource, which survives browser reloads (since Coder does too)
class State:
    keys = set()

    def init(self, key, val=None):
        if key in self.keys:
            return

        self.keys.add(key)
        setattr(self, key, val)
        return True


@st.cache_resource
def get_state():
    return State()


@st.cache_resource
def get_coder():
    coder = cli_main(return_coder=True)
    if not isinstance(coder, Coder):
        raise ValueError(coder)
    if not coder.repo:
        raise ValueError("GUI can currently only be used inside a git repo")

    io = BrowserIO(
        pretty=False,
        yes=False,  # Don't auto-answer, let user decide
        dry_run=coder.io.dry_run,
        encoding=coder.io.encoding,
    )
    # coder.io = io # this breaks the input_history
    coder.commands.io = io

    for line in coder.get_announcements():
        coder.io.tool_output(line)

    return coder


class GUI:
    prompt = None
    prompt_as = "user"
    last_undo_empty = None
    recent_msgs_empty = None
    web_content_empty = None

    def announce(self):
        lines = self.coder.get_announcements()
        lines = "  \n".join(lines)
        return lines

    def show_edit_info(self, edit):
        commit_hash = edit.get("commit_hash")
        commit_message = edit.get("commit_message")
        diff = edit.get("diff")
        fnames = edit.get("fnames")
        if fnames:
            fnames = sorted(fnames)

        if not commit_hash and not fnames:
            return

        show_undo = False
        res = ""
        if commit_hash:
            res += f"Commit `{commit_hash}`: {commit_message}  \n"
            if commit_hash == self.coder.last_aider_commit_hash:
                show_undo = True

        if fnames:
            fnames = [f"`{fname}`" for fname in fnames]
            fnames = ", ".join(fnames)
            res += f"Applied edits to {fnames}."

        if diff:
            with st.expander(res):
                st.code(diff, language="diff")
                if show_undo:
                    self.add_undo(commit_hash)
        else:
            with st.container(border=True):
                st.write(res)
                if show_undo:
                    self.add_undo(commit_hash)

    def add_undo(self, commit_hash):
        if self.last_undo_empty:
            self.last_undo_empty.empty()

        self.last_undo_empty = st.empty()
        undone = self.state.last_undone_commit_hash == commit_hash
        if not undone:
            with self.last_undo_empty:
                if self.button(f"Undo commit `{commit_hash}`", key=f"undo_{commit_hash}"):
                    self.do_undo(commit_hash)

    def do_sidebar(self):
        with st.sidebar:
            st.title("Aider")
            
            # Create tabs for different sections
            main_tab, settings_tab = st.tabs(["Main", "Settings"])
            
            with main_tab:
                self.do_add_to_chat()
                self.do_chat_history_management()
                self.do_recent_msgs()
                self.do_clear_chat_history()
                
                st.warning(
                    "This browser version of aider is experimental. Please share feedback in [GitHub"
                    " issues](https://github.com/Aider-AI/aider/issues)."
                )
            
            with settings_tab:
                self.do_prompt_settings()

    def do_prompt_settings(self):
        """Settings UI for managing prompt preferences"""
        st.subheader("🔧 Prompt Preferences")
        st.write("Configure how aider handles different types of confirmation prompts.")
        
        st.info("💡 **Default settings optimized for smooth development workflow**: Auto-approve routine tasks (file creation, lint fixes, package installs), always ask for security-critical operations (shell commands), and reduce noise from URLs.")
        
        # Get the browser config
        browser_config = self.coder.commands.io.browser_config
        all_prefs = browser_config.get_all_preferences()
        
        # Track if any changes were made
        changes_made = False
        
        for category_name, category_prefs in all_prefs.items():
            # Create a nice display name for the category
            display_name = category_name.replace("_", " ").title()
            
            with st.expander(f"📁 {display_name}", expanded=False):
                for pref_key, current_value in category_prefs.items():
                    # Create a nice display name for the preference
                    pref_display = pref_key.replace("_", " ").title()
                    
                    # Create selectbox for this preference
                    options = ["ask", "always_yes", "always_no"]
                    option_labels = ["🤔 Ask me", "✅ Always Yes", "❌ Always No"]
                    
                    try:
                        current_index = options.index(current_value)
                    except ValueError:
                        current_index = 0  # Default to "ask"
                    
                    new_value = st.selectbox(
                        pref_display,
                        options,
                        index=current_index,
                        format_func=lambda x: option_labels[options.index(x)],
                        key=f"pref_{category_name}_{pref_key}",
                        help=self._get_preference_help(pref_key)
                    )
                    
                    # Check if value changed
                    if new_value != current_value:
                        browser_config.update_preference(pref_key, new_value)
                        changes_made = True
        
        # Save button and status
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Settings", disabled=not changes_made):
                if browser_config.save_config():
                    st.success("Settings saved!")
                    st.rerun()
                else:
                    st.error("Failed to save settings")
        
        with col2:
            if st.button("🔄 Reset to Defaults"):
                browser_config.config = browser_config.get_default_config()
                if browser_config.save_config():
                    st.success("Settings reset to defaults!")
                    st.rerun()
                else:
                    st.error("Failed to reset settings")
        
        # UI Settings section
        st.subheader("🎨 Interface Settings")
        
        # Auto-load recent history setting
        current_auto_load = browser_config.config.get("ui_settings", {}).get("auto_load_recent_history", False)
        auto_load = st.checkbox(
            "🔄 Auto-load most recent chat history on startup",
            value=current_auto_load,
            help="Automatically load the most recent chat history file when starting browser mode"
        )
        
        if auto_load != current_auto_load:
            browser_config.config.setdefault("ui_settings", {})["auto_load_recent_history"] = auto_load
            changes_made = True
        
        # Show config file location
        st.info(f"📄 Config file: `{browser_config.config_path}`")
    
    def _get_preference_help(self, pref_key):
        """Get help text for different preference types"""
        help_text = {
            "create_new_file": "When aider wants to create a new file that doesn't exist (Default: Always Yes - streamlines development)",
            "add_file_to_chat": "When aider mentions a file not currently in the chat (Default: Always Yes - keeps context complete)", 
            "edit_file_not_in_chat": "When aider wants to edit a file not added to chat (Default: Ask - important decision)",
            "create_from_pattern": "When file patterns don't match existing files (Default: Always Yes - reduces friction)",
            "run_shell_commands": "When aider suggests running shell commands (Default: Ask - security critical)",
            "add_command_output": "Whether to include command output in the chat (Default: Always Yes - useful context)",
            "add_run_output": "Whether to include /run command output in chat (Default: Always Yes - useful context)",
            "pip_install": "When aider wants to install Python packages (Default: Always Yes - routine task)",
            "install_playwright": "When aider needs to install playwright for web scraping (Default: Always Yes - routine task)",
            "openrouter_login": "When aider offers OpenRouter OAuth login (Default: Ask - user choice)",
            "fix_lint_errors": "When aider wants to automatically fix lint errors (Default: Always Yes - helpful automation)",
            "fix_test_errors": "When aider wants to automatically fix test failures (Default: Always Yes - helpful automation)",
            "context_window_exceeded": "When message would exceed model's context window (Default: Ask - user needs to know)",
            "add_url_to_chat": "When aider detects URLs in your input (Default: Always No - reduces noise)",
            "open_documentation_url": "When aider offers to open documentation links (Default: Always No - reduces interruptions)",
            "create_git_repo": "When aider suggests creating a git repository (Default: Always Yes - recommended setup)",
            "add_to_gitignore": "When aider suggests adding patterns to .gitignore (Default: Always Yes - good practice)",
            "analytics_opt_in": "Whether to allow anonymous analytics collection (Default: Ask - privacy choice)",
            "execute_plan": "In architect mode, whether to execute the generated plan (Default: Ask - important decision)"
        }
        return help_text.get(pref_key, "Configure this prompt preference")

    def do_recommended_actions(self):
        text = "Aider works best when your code is stored in a git repo.  \n"
        text += f"[See the FAQ for more info]({urls.git})"

        with st.expander("Recommended actions", expanded=True):
            with st.popover("Create a git repo to track changes"):
                st.write(text)
                self.button("Create git repo", key=random.random(), help="?")

            with st.popover("Update your `.gitignore` file"):
                st.write("It's best to keep aider's internal files out of your git repo.")
                self.button("Add `.aider*` to `.gitignore`", key=random.random(), help="?")

    def do_add_to_chat(self):
        # with st.expander("Add to the chat", expanded=True):
        self.do_add_files()
        self.do_add_web_page()

    def do_add_files(self):
        fnames = st.multiselect(
            "Add files to the chat",
            self.coder.get_all_relative_files(),
            default=list(self.coder.get_inchat_relative_files()),
            placeholder="Files to edit",
            disabled=self.prompt_pending(),
            help=(
                "Only add the files that need to be *edited* for the task you are working"
                " on. Aider will pull in other relevant code to provide context to the LLM."
            ),
        )

        for fname in fnames:
            if fname not in self.coder.get_inchat_relative_files():
                self.coder.add_rel_fname(fname)
                self.info(f"Added {fname} to the chat")

        for fname in self.coder.get_inchat_relative_files():
            if fname not in fnames:
                self.coder.drop_rel_fname(fname)
                self.info(f"Removed {fname} from the chat")

    def do_add_web_page(self):
        with st.popover("Add a web page to the chat"):
            self.do_web()

    def do_add_image(self):
        with st.popover("Add image"):
            st.markdown("Hello World 👋")
            st.file_uploader("Image file", disabled=self.prompt_pending())

    def do_run_shell(self):
        with st.popover("Run shell commands, tests, etc"):
            st.markdown(
                "Run a shell command and optionally share the output with the LLM. This is"
                " a great way to run your program or run tests and have the LLM fix bugs."
            )
            st.text_input("Command:")
            st.radio(
                "Share the command output with the LLM?",
                [
                    "Review the output and decide whether to share",
                    "Automatically share the output on non-zero exit code (ie, if any tests fail)",
                ],
            )
            st.selectbox(
                "Recent commands",
                [
                    "my_app.py --doit",
                    "my_app.py --cleanup",
                ],
                disabled=self.prompt_pending(),
            )

    def do_tokens_and_cost(self):
        with st.expander("Tokens and costs", expanded=True):
            pass

    def do_show_token_usage(self):
        with st.popover("Show token usage"):
            st.write("hi")

    def do_chat_history_management(self):
        """UI for loading and managing chat history"""
        with st.expander("💬 Chat History", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📂 Load Previous Session", help="Load chat history from a previous session"):
                    self._show_history_loader()
            
            with col2:
                if st.button("💾 Save Current Session", help="Save current chat to history file"):
                    self._save_current_session()
            
            # Show current history file info
            history_file = getattr(self.coder.io, 'chat_history_file', None)
            if history_file:
                import os
                if os.path.exists(history_file):
                    st.info(f"📄 Current history: `{os.path.basename(history_file)}`")
                else:
                    st.info(f"📄 History file: `{os.path.basename(history_file)}` (will be created)")
    
    def _show_history_loader(self):
        """Show interface for loading chat history"""
        self.state.init("show_history_loader", False)
        self.state.show_history_loader = True
        st.rerun()
    
    def _save_current_session(self):
        """Save current chat session to history file"""
        try:
            # Force save current session
            if hasattr(self.coder, 'cur_messages') and self.coder.cur_messages:
                # Append current messages to done messages
                self.coder.done_messages.extend(self.coder.cur_messages)
                self.coder.cur_messages = []
                
                # Save to history file
                self.coder.io.append_chat_history(self.coder.done_messages[-10:])  # Save last 10 messages
                st.success("💾 Session saved to chat history!")
            else:
                st.warning("No chat messages to save")
        except Exception as e:
            st.error(f"Failed to save session: {str(e)}")

    def do_clear_chat_history(self):
        text = "Saves tokens, reduces confusion"
        if self.button("🗑️ Clear Current Chat", help=text):
            self.coder.done_messages = []
            self.coder.cur_messages = []
            # Clear browser state messages too
            self.state.messages = [
                dict(role="info", content=self.announce()),
            ]
            self.info("Cleared chat history. Now the LLM can't see anything before this line.")

    def do_show_metrics(self):
        st.metric("Cost of last message send & reply", "$0.0019", help="foo")
        st.metric("Cost to send next message", "$0.0013", help="foo")
        st.metric("Total cost this session", "$0.22")

    def do_git(self):
        with st.expander("Git", expanded=False):
            # st.button("Show last diff")
            # st.button("Undo last commit")
            self.button("Commit any pending changes")
            with st.popover("Run git command"):
                st.markdown("## Run git command")
                st.text_input("git", value="git ")
                self.button("Run")
                st.selectbox(
                    "Recent git commands",
                    [
                        "git checkout -b experiment",
                        "git stash",
                    ],
                    disabled=self.prompt_pending(),
                )

    def do_recent_msgs(self):
        if not self.recent_msgs_empty:
            self.recent_msgs_empty = st.empty()

        if self.prompt_pending():
            self.recent_msgs_empty.empty()
            self.state.recent_msgs_num += 1

        with self.recent_msgs_empty:
            self.old_prompt = st.selectbox(
                "Resend a recent chat message",
                self.state.input_history,
                placeholder="Choose a recent chat message",
                # label_visibility="collapsed",
                index=None,
                key=f"recent_msgs_{self.state.recent_msgs_num}",
                disabled=self.prompt_pending(),
            )
            if self.old_prompt:
                self.prompt = self.old_prompt

    def do_messages_container(self):
        self.messages = st.container()

        # stuff a bunch of vertical whitespace at the top
        # to get all the chat text to the bottom
        # self.messages.container(height=300, border=False)

        with self.messages:
            for msg in self.state.messages:
                role = msg["role"]

                if role == "edit":
                    self.show_edit_info(msg)
                elif role == "info":
                    # Check if this is the session announcement (contains version and model info)
                    content = msg["content"]
                    if "Aider v" in content and ("Main model:" in content or "Git repo:" in content):
                        # This is the session announcement - make it collapsible
                        lines = content.split("  \n")
                        if lines:
                            # Use the first line as the summary and add session cost
                            summary = lines[0]
                            # Format cost with appropriate precision
                            cost = self.coder.total_cost
                            if cost >= 0.01:
                                cost_str = f"${cost:.2f}"
                            else:
                                cost_str = f"${cost:.4f}"
                            
                            with st.expander(f"ℹ️ {summary} • Session cost: {cost_str}", expanded=False):
                                st.markdown(f"```\n{content}\n```")
                    elif "\n" in content or any(word in content.lower() for word in ["token", "cost", "usage", "commit"]):
                        # Regular info with code formatting
                        st.markdown(f"```\n{content}\n```")
                    else:
                        # Simple info message
                        st.info(content)
                elif role == "text":
                    text = msg["content"]
                    line = text.splitlines()[0]
                    with self.messages.expander(line):
                        st.text(text)
                elif role in ("user", "assistant"):
                    with st.chat_message(role):
                        st.write(msg["content"])
                        # self.cost()
                else:
                    st.dict(msg)

    def initialize_state(self):
        messages = [
            dict(role="info", content=self.announce()),
        ]

        self.state.init("messages", messages)
        self.state.init("last_aider_commit_hash", self.coder.last_aider_commit_hash)
        self.state.init("last_undone_commit_hash")
        self.state.init("recent_msgs_num", 0)
        self.state.init("web_content_num", 0)
        self.state.init("prompt")
        self.state.init("scraper")
        self.state.init("pending_confirmation", None)
        self.state.init("confirmation_response", None)
        self.state.init("pending_command", None)  # Track command waiting for confirmation

        self.state.init("initial_inchat_files", self.coder.get_inchat_relative_files())

        if "input_history" not in self.state.keys:
            input_history = list(self.coder.io.get_input_history())
            seen = set()
            input_history = [x for x in input_history if not (x in seen or seen.add(x))]
            self.state.input_history = input_history
            self.state.keys.add("input_history")

    def button(self, args, **kwargs):
        "Create a button, disabled if prompt pending"

        # Force everything to be disabled if there is a prompt pending
        if self.prompt_pending():
            kwargs["disabled"] = True

        return st.button(args, **kwargs)

    def __init__(self):
        self.coder = get_coder()
        self.state = get_state()
        self.command_handled = False

        # Set the state reference in the BrowserIO
        if isinstance(self.coder.commands.io, BrowserIO):
            self.coder.commands.io.gui_state = self.state

        # Force the coder to cooperate, regardless of cmd line args
        self.coder.yield_stream = True
        self.coder.stream = True
        self.coder.pretty = False

        self.initialize_state()
        
        # Auto-load recent history if configured
        self._auto_load_recent_history()

        self.do_messages_container()
        self.do_sidebar()
        
        # Handle confirmation prompts
        self.do_confirmation_prompt()
        
        # Handle history loader
        self.do_history_loader_modal()

        # Disable input if there's a pending confirmation
        input_disabled = self.state.pending_confirmation is not None
        input_placeholder = "Please respond to the confirmation above" if input_disabled else "Say something (or use /add, /drop, /help, etc.)"
        
        user_inp = st.chat_input(input_placeholder, disabled=input_disabled)
        if user_inp and not input_disabled:
            self.prompt = user_inp

        # Check if we need to resume a command after confirmation
        if not input_disabled and self.state.confirmation_response and self.state.pending_command:
            # Resume the pending command
            self._resume_after_confirmation()
            return

        if self.prompt_pending() and not input_disabled:
            self.process_chat()

        if not self.prompt or self.command_handled:
            return

        self.state.prompt = self.prompt

        if self.prompt_as == "user":
            self.coder.io.add_to_input_history(self.prompt)

        self.state.input_history.append(self.prompt)

        if self.prompt_as:
            self.state.messages.append({"role": self.prompt_as, "content": self.prompt})
        if self.prompt_as == "user":
            with self.messages.chat_message("user"):
                st.write(self.prompt)
        elif self.prompt_as == "text":
            line = self.prompt.splitlines()[0]
            line += "??"
            with self.messages.expander(line):
                st.text(self.prompt)

        # re-render the UI for the prompt_pending state
        st.rerun()

    def prompt_pending(self):
        return self.state.prompt is not None

    def cost(self):
        cost = random.random() * 0.003 + 0.001
        st.caption(f"${cost:0.4f}")

    def process_chat(self):
        prompt = self.state.prompt
        self.state.prompt = None

        try:
            # Check if this is a slash command first
            if prompt and self.coder.commands.is_command(prompt):
                # Handle slash commands
                self.handle_command(prompt)
                # Mark that we handled a command to prevent double processing
                self.command_handled = True
                return

            # This duplicates logic from within Coder
            self.num_reflections = 0
            self.max_reflections = 3

            while prompt:
                with self.messages.chat_message("assistant"):
                    res = st.write_stream(self.coder.run_stream(prompt))
                    self.state.messages.append({"role": "assistant", "content": res})
                    # self.cost()

                prompt = None
                if self.coder.reflected_message:
                    if self.num_reflections < self.max_reflections:
                        self.num_reflections += 1
                        self.info(self.coder.reflected_message)
                        prompt = self.coder.reflected_message

            with self.messages:
                edit = dict(
                    role="edit",
                    fnames=self.coder.aider_edited_files,
                )
                if self.state.last_aider_commit_hash != self.coder.last_aider_commit_hash:
                    edit["commit_hash"] = self.coder.last_aider_commit_hash
                    edit["commit_message"] = self.coder.last_aider_commit_message
                    commits = f"{self.coder.last_aider_commit_hash}~1"
                    diff = self.coder.repo.diff_commits(
                        self.coder.pretty,
                        commits,
                        self.coder.last_aider_commit_hash,
                    )
                    edit["diff"] = diff
                    self.state.last_aider_commit_hash = self.coder.last_aider_commit_hash

                self.state.messages.append(edit)
                self.show_edit_info(edit)

            # re-render the UI for the non-prompt_pending state
            st.rerun()
            
        except BrowserPromptException as e:
            # LLM processing needs user confirmation - store the command to resume later
            self.state.pending_command = {
                "type": "chat",
                "prompt": prompt
            }
            st.rerun()

    def handle_command(self, prompt):
        """Handle slash commands in the browser interface"""
        from aider.commands import SwitchCoder
        
        # Don't manually display the command here - let the main flow handle it
        # This prevents double display of the user input
        
        # Capture command output using the same CaptureIO that's already set up
        self.coder.commands.io.get_captured_lines()  # Clear any previous output
        
        result = None
        try:
            # Run the command
            result = self.coder.commands.run(prompt)
            
        except BrowserPromptException as e:
            # Command needs user confirmation - but still show output that was captured
            pass
        
        # Always get and display any output that was captured, even if there was an exception
        captured_lines = self.coder.commands.io.get_captured_lines()
        
        # Display command output if any
        if captured_lines:
            output = "\n".join(captured_lines)
            self.info(output)
        
        # Check if we had a prompt exception and handle it
        if self.state.pending_confirmation:
            # Command needs user confirmation - the command has already executed and shown output
            # We don't need to store anything special, the confirmation will be handled
            # by the prompt UI and the response will be processed by confirm_ask
            return
        
        # Continue with normal result handling if no exception
        try:
            # If the command returned a result (like some commands that need to show info)
            if result and captured_lines:
                # Don't duplicate output if we already showed captured lines
                pass
            elif result:
                self.info(str(result))
                
            # Some commands might return a prompt to send to the LLM
            if result and isinstance(result, str) and not captured_lines:
                # This handles commands like /undo that might return a prompt
                with self.messages.chat_message("assistant"):
                    res = st.write_stream(self.coder.run_stream(result))
                    self.state.messages.append({"role": "assistant", "content": res})
            
        except SwitchCoder as e:
            # Some commands like /model, /chat-mode etc. throw SwitchCoder
            # In browser mode, we'll just show a message that these aren't supported yet
            self.info(f"Command '{prompt}' requires switching coder configuration, which is not yet supported in browser mode.")
            
        except Exception as e:
            self.info(f"Command error: {str(e)}")
        
        # Force UI refresh to show command results
        st.rerun()
    
    def do_confirmation_prompt(self):
        """Display confirmation prompts and handle user responses"""
        if self.state.pending_confirmation:
            prompt_data = self.state.pending_confirmation
            
            st.warning("⚠️ Confirmation Required")
            
            # Display the subject if provided
            if prompt_data.get("subject"):
                st.info(prompt_data["subject"])
            
            # Display the question
            st.write(prompt_data["question"])
            
            # Create buttons for user responses
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("✅ Yes", key="confirm_yes"):
                    self.state.confirmation_response = "yes"
                    self.state.pending_confirmation = None
                    self._resume_after_confirmation()
            
            with col2:
                if st.button("❌ No", key="confirm_no"):
                    self.state.confirmation_response = "no"
                    self.state.pending_confirmation = None
                    self._resume_after_confirmation()
            
            # Add additional buttons based on available options
            if prompt_data.get("group") and not prompt_data.get("explicit_yes_required"):
                with col3:
                    if st.button("✅ All", key="confirm_all"):
                        self.state.confirmation_response = "all"
                        self.state.pending_confirmation = None
                        self._resume_after_confirmation()
            
            if prompt_data.get("group"):
                with col4:
                    if st.button("⏭️ Skip All", key="confirm_skip"):
                        self.state.confirmation_response = "skip"
                        self.state.pending_confirmation = None
                        self._resume_after_confirmation()
            
            if prompt_data.get("allow_never"):
                with col5:
                    if st.button("🚫 Don't Ask Again", key="confirm_never"):
                        self.state.confirmation_response = "don't"
                        self.state.pending_confirmation = None
                        self._resume_after_confirmation()
            
            # Disable other UI elements while waiting for confirmation
            return True
        
        return False
    
    def do_history_loader_modal(self):
        """Show modal for loading chat history"""
        if getattr(self.state, 'show_history_loader', False):
            with st.container():
                st.subheader("📂 Load Previous Chat Session")
                
                # Look for history files in current directory and common locations
                history_files = self._find_history_files()
                
                if not history_files:
                    st.warning("No chat history files found in current directory or common locations.")
                    st.info("💡 History files are typically named `.aider.chat.history.md`")
                    if st.button("❌ Cancel"):
                        self.state.show_history_loader = False
                        st.rerun()
                    return
                
                # Let user select from available history files
                selected_file = st.selectbox(
                    "Select a chat history file to load:",
                    options=history_files,
                    format_func=lambda x: f"{x['display_name']} ({x['messages']} messages, {x['age']})",
                    help="Choose a previous chat session to continue from"
                )
                
                if selected_file:
                    # Show preview of the selected file
                    with st.expander("📋 Preview", expanded=False):
                        preview = self._get_history_preview(selected_file['path'])
                        st.text(preview)
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("✅ Load Session", disabled=not selected_file):
                        self._load_chat_history(selected_file['path'])
                        self.state.show_history_loader = False
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Refresh List"):
                        st.rerun()
                
                with col3:
                    if st.button("❌ Cancel"):
                        self.state.show_history_loader = False
                        st.rerun()
    
    def _find_history_files(self):
        """Find available chat history files"""
        import os
        import glob
        from datetime import datetime
        
        history_files = []
        
        # Common locations to search
        search_paths = [
            ".",  # Current directory
            os.path.expanduser("~"),  # Home directory
        ]
        
        # If we're in a git repo, also search git root
        if hasattr(self.coder, 'root') and self.coder.root:
            search_paths.append(self.coder.root)
        
        for search_path in search_paths:
            # Look for .aider.chat.history.md files
            pattern = os.path.join(search_path, ".aider.chat.history*.md")
            for file_path in glob.glob(pattern):
                if os.path.isfile(file_path):
                    try:
                        # Get file info
                        stat = os.stat(file_path)
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        age = self._format_time_ago(mtime)
                        
                        # Count messages in file
                        message_count = self._count_messages_in_file(file_path)
                        
                        # Create display name
                        rel_path = os.path.relpath(file_path)
                        display_name = rel_path if len(rel_path) < len(file_path) else os.path.basename(file_path)
                        
                        history_files.append({
                            'path': file_path,
                            'display_name': display_name,
                            'messages': message_count,
                            'age': age,
                            'mtime': mtime
                        })
                    except Exception:
                        continue
        
        # Sort by modification time (newest first)
        history_files.sort(key=lambda x: x['mtime'], reverse=True)
        return history_files
    
    def _count_messages_in_file(self, file_path):
        """Count messages in a chat history file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Count lines starting with #### (user messages)
            return len([line for line in content.split('\n') if line.startswith('#### ')])
        except Exception:
            return 0
    
    def _format_time_ago(self, dt):
        """Format time ago in human readable format"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 7:
            return dt.strftime("%b %d, %Y")
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    def _get_history_preview(self, file_path):
        """Get a preview of the chat history file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get first few lines and last few lines
            lines = content.split('\n')
            if len(lines) <= 20:
                return content
            else:
                preview_lines = lines[:10] + ['...', '(truncated)', '...'] + lines[-10:]
                return '\n'.join(preview_lines)
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _load_chat_history(self, file_path):
        """Load chat history from file"""
        try:
            from aider import utils
            
            # Read the history file
            with open(file_path, 'r', encoding='utf-8') as f:
                history_md = f.read()
            
            if not history_md.strip():
                st.warning("Selected history file is empty")
                return
            
            # Parse the markdown into messages
            done_messages = utils.split_chat_history_markdown(history_md)
            
            if not done_messages:
                st.warning("No valid messages found in history file")
                return
            
            # Clear current chat and load history
            self.coder.done_messages = done_messages
            self.coder.cur_messages = []
            
            # Convert to browser state format and display
            browser_messages = [dict(role="info", content=self.announce())]
            
            for msg in done_messages[-20:]:  # Show last 20 messages
                if msg.get('role') in ('user', 'assistant'):
                    browser_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            self.state.messages = browser_messages
            
            # Update the chat history file reference
            self.coder.io.chat_history_file = file_path
            
            st.success(f"✅ Loaded {len(done_messages)} messages from chat history!")
            self.info(f"Loaded chat history from {os.path.basename(file_path)} ({len(done_messages)} messages)")
            
        except Exception as e:
            st.error(f"Failed to load chat history: {str(e)}")
    
    def _auto_load_recent_history(self):
        """Auto-load the most recent chat history if configured"""
        try:
            # Check if auto-loading is enabled in config
            browser_config = self.coder.commands.io.browser_config
            auto_load = browser_config.config.get("ui_settings", {}).get("auto_load_recent_history", False)
            
            if not auto_load:
                return
            
            # Only auto-load if we don't already have messages (fresh start)
            if len(self.state.messages) > 1:  # More than just the announcement
                return
            
            # Find the most recent history file
            history_files = self._find_history_files()
            if not history_files:
                return
            
            # Load the most recent file
            most_recent = history_files[0]  # Already sorted by mtime
            self._load_chat_history(most_recent['path'])
            
        except Exception:
            # Silently fail auto-loading - don't interrupt startup
            pass
    
    def _resume_after_confirmation(self):
        """Resume processing after user responds to confirmation"""
        # Check if there's a pending operation to complete
        browser_io = self.coder.commands.io
        if hasattr(browser_io, 'pending_operation') and browser_io.pending_operation:
            operation = browser_io.pending_operation
            browser_io.pending_operation = None
            
            # Get the user's response
            response = self.state.confirmation_response
            
            if operation["type"] == "add_to_chat" and response == "yes":
                # Complete the add-to-chat operation
                self._complete_add_to_chat_operation(operation)
        
        # If there's a pending command, resume it
        if self.state.pending_command:
            pending_cmd = self.state.pending_command
            self.state.pending_command = None
            if pending_cmd["type"] == "slash_command":
                self.handle_command(pending_cmd["prompt"])
            elif pending_cmd["type"] == "chat":
                # For chat processing, we'll trigger it by setting the prompt
                self.state.prompt = pending_cmd["prompt"]
        
        st.rerun()
    
    def _complete_add_to_chat_operation(self, operation):
        """Complete the add-to-chat operation for /run command"""
        from aider import prompts
        
        command = operation["command"]
        output = operation["output"]
        
        # Calculate number of lines for the confirmation message
        num_lines = len(output.strip().splitlines())
        line_plural = "line" if num_lines == 1 else "lines"
        self.info(f"Added {num_lines} {line_plural} of output to the chat.")
        
        # Format the message for chat history
        msg = prompts.run_output.format(
            command=command,
            output=output,
        )
        
        # Add to chat history
        self.coder.cur_messages += [
            dict(role="user", content=msg),
            dict(role="assistant", content="Ok."),
        ]

    def info(self, message, echo=True):
        info = dict(role="info", content=message)
        self.state.messages.append(info)

        # We will render the tail of the messages array after this call
        if echo:
            self.messages.info(message)

    def do_web(self):
        st.markdown("Add the text content of a web page to the chat")

        if not self.web_content_empty:
            self.web_content_empty = st.empty()

        if self.prompt_pending():
            self.web_content_empty.empty()
            self.state.web_content_num += 1

        with self.web_content_empty:
            self.web_content = st.text_input(
                "URL",
                placeholder="https://...",
                key=f"web_content_{self.state.web_content_num}",
            )

        if not self.web_content:
            return

        url = self.web_content

        if not self.state.scraper:
            self.scraper = Scraper(print_error=self.info, playwright_available=has_playwright())

        content = self.scraper.scrape(url) or ""
        if content.strip():
            content = f"{url}\n\n" + content
            self.prompt = content
            self.prompt_as = "text"
        else:
            self.info(f"No web content found for `{url}`.")
            self.web_content = None

    def do_undo(self, commit_hash):
        self.last_undo_empty.empty()

        if (
            self.state.last_aider_commit_hash != commit_hash
            or self.coder.last_aider_commit_hash != commit_hash
        ):
            self.info(f"Commit `{commit_hash}` is not the latest commit.")
            return

        self.coder.commands.io.get_captured_lines()
        reply = self.coder.commands.cmd_undo(None)
        lines = self.coder.commands.io.get_captured_lines()

        lines = "\n".join(lines)
        lines = lines.splitlines()
        lines = "  \n".join(lines)
        self.info(lines, echo=False)

        self.state.last_undone_commit_hash = commit_hash

        if reply:
            self.prompt_as = None
            self.prompt = reply


def gui_main():
    st.set_page_config(
        layout="wide",
        page_title="Aider",
        page_icon=urls.favicon,
        menu_items={
            "Get Help": urls.website,
            "Report a bug": "https://github.com/Aider-AI/aider/issues",
            "About": "# Aider\nAI pair programming in your browser.",
        },
    )

    # config_options = st.config._config_options
    # for key, value in config_options.items():
    #    print(f"{key}: {value.value}")

    GUI()


if __name__ == "__main__":
    status = gui_main()
    sys.exit(status)
