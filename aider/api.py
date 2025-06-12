#!/usr/bin/env python

import json
import threading
import traceback
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Optional, Dict, Any

try:
    from flask import Flask, request, jsonify
except ImportError:
    Flask = None

from aider.coders import Coder
from aider.io import InputOutput
from aider.main import main as cli_main


class APIPromptException(Exception):
    """Exception raised when API needs to prompt user for input"""
    def __init__(self, prompt_data):
        self.prompt_data = prompt_data
        super().__init__("API prompt required")


class APIIO(InputOutput):
    """Custom IO class for API mode that captures output and handles prompts"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.captured_lines = []
        self.command_in_progress = False
        self.pending_prompt = None
        
    def tool_output(self, *messages, log_only=False):
        if not log_only and messages:
            self.captured_lines.append(" ".join(str(msg) for msg in messages))
        super().tool_output(*messages, log_only=log_only)

    def tool_error(self, msg):
        self.captured_lines.append(f"ERROR: {msg}")
        super().tool_error(msg)

    def tool_warning(self, msg):
        self.captured_lines.append(f"WARNING: {msg}")
        super().tool_warning(msg)

    def get_captured_output(self):
        """Get and clear captured output"""
        output = "\n".join(self.captured_lines)
        self.captured_lines = []
        return output

    def confirm_ask(
        self,
        question,
        default="y",
        subject=None,
        explicit_yes_required=False,
        group=None,
        allow_never=False,
    ):
        """Override confirm_ask to handle interactive prompts in API mode"""
        self.num_user_asks += 1
        self.ring_bell()

        question_id = (question, subject)
        if question_id in self.never_prompts:
            return False

        # Store the prompt details for API response
        prompt_data = {
            "question": question,
            "subject": subject,
            "default": default,
            "explicit_yes_required": explicit_yes_required,
            "group": group,
            "allow_never": allow_never,
            "type": "confirmation"
        }
        
        self.pending_prompt = prompt_data
        raise APIPromptException(prompt_data)


@dataclass
class CommandResult:
    """Result of executing a command"""
    output: str
    status: str  # "completed", "error", "needs_input"
    prompt_data: Optional[Dict[str, Any]] = None


class APIServer:
    """Flask API server for aider"""
    
    def __init__(self):
        if Flask is None:
            raise ImportError("Flask is required for API mode. Install with: pip install flask")
        
        self.app = Flask(__name__)
        self.coder = None
        self.command_queue = Queue()
        self.result_queue = Queue()
        self.command_in_progress = False
        self.command_lock = threading.Lock()
        
        self._setup_routes()
        self._initialize_coder()
        
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "healthy", "version": "1.0"})
        
        @self.app.route('/status', methods=['GET'])
        def status():
            return jsonify({
                "command_in_progress": self.command_in_progress,
                "queue_size": self.command_queue.qsize()
            })
        
        @self.app.route('/command', methods=['POST'])
        def execute_command():
            return self._handle_command_request()
    
    def _initialize_coder(self):
        """Initialize the aider coder instance"""
        try:
            self.coder = cli_main(return_coder=True)
            if not isinstance(self.coder, Coder):
                raise ValueError("Failed to initialize coder")
            
            # Replace IO with our custom API IO
            api_io = APIIO(
                pretty=False,
                yes=False,
                dry_run=self.coder.io.dry_run,
                encoding=self.coder.io.encoding,
            )
            
            # Update coder IO references
            old_io = self.coder.io
            self.coder.io = api_io
            self.coder.commands.io = api_io
            
            # Copy important settings from old IO
            api_io.chat_history_file = old_io.chat_history_file
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize aider coder: {e}")
    
    def _handle_command_request(self) -> dict:
        """Handle incoming command requests"""
        try:
            # Check if we're already processing a command
            with self.command_lock:
                if self.command_in_progress:
                    return jsonify({
                        "error": "Command in progress",
                        "message": "Please wait for current command to complete"
                    }), 409
                
                # Mark as in progress
                self.command_in_progress = True
            
            # Get command from request
            data = request.get_json()
            if not data or 'command' not in data:
                self.command_in_progress = False
                return jsonify({
                    "error": "Invalid request",
                    "message": "Request must contain 'command' field"
                }), 400
            
            command = data['command']
            
            # Execute the command
            result = self._execute_command(command)
            
            # Mark as no longer in progress
            self.command_in_progress = False
            
            # Return result
            if result.status == "error":
                return jsonify({
                    "error": result.output,
                    "status": result.status
                }), 500
            elif result.status == "needs_input":
                return jsonify({
                    "output": result.output,
                    "status": result.status,
                    "prompt": result.prompt_data
                }), 200
            else:
                return jsonify({
                    "output": result.output,
                    "status": result.status
                }), 200
                
        except Exception as e:
            self.command_in_progress = False
            return jsonify({
                "error": "Internal server error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }), 500
    
    def _execute_command(self, command: str) -> CommandResult:
        """Execute a single aider command"""
        try:
            # Clear any previous output
            self.coder.io.get_captured_output()
            
            # Check if this is a slash command
            if command.startswith('/') or self.coder.commands.is_command(command):
                return self._execute_slash_command(command)
            else:
                return self._execute_chat_command(command)
                
        except APIPromptException as e:
            # Command needs user input
            output = self.coder.io.get_captured_output()
            return CommandResult(
                output=output,
                status="needs_input",
                prompt_data=e.prompt_data
            )
        except Exception as e:
            output = self.coder.io.get_captured_output()
            error_output = f"{output}\nERROR: {str(e)}"
            return CommandResult(
                output=error_output,
                status="error"
            )
    
    def _execute_slash_command(self, command: str) -> CommandResult:
        """Execute a slash command like /add, /drop, etc."""
        try:
            result = self.coder.commands.run(command)
            output = self.coder.io.get_captured_output()
            
            return CommandResult(
                output=output,
                status="completed"
            )
        except APIPromptException:
            # Re-raise APIPromptException so it can be handled by _execute_command
            raise
        except Exception as e:
            output = self.coder.io.get_captured_output()
            error_output = f"{output}\nCommand failed: {str(e)}"
            return CommandResult(
                output=error_output,
                status="error"
            )
    
    def _execute_chat_command(self, message: str) -> CommandResult:
        """Execute a chat message to the LLM"""
        try:
            # Add message to input history
            self.coder.io.add_to_input_history(message)
            
            # Run the message through the coder
            response = ""
            for chunk in self.coder.run_stream(message):
                response += chunk
            
            # Get any additional output
            output = self.coder.io.get_captured_output()
            if output:
                full_output = f"{output}\n\nAssistant: {response}"
            else:
                full_output = f"Assistant: {response}"
            
            return CommandResult(
                output=full_output,
                status="completed"
            )
        except APIPromptException:
            # Re-raise APIPromptException so it can be handled by _execute_command
            raise
        except Exception as e:
            output = self.coder.io.get_captured_output()
            error_output = f"{output}\nChat failed: {str(e)}"
            return CommandResult(
                output=error_output,
                status="error"
            )
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Run the Flask API server"""
        print(f"Starting aider API server on {host}:{port}")
        print("Available endpoints:")
        print(f"  GET  http://{host}:{port}/health")
        print(f"  GET  http://{host}:{port}/status") 
        print(f"  POST http://{host}:{port}/command")
        print("\nExample usage:")
        print(f"  curl -X POST http://{host}:{port}/command -H 'Content-Type: application/json' -d '{{\"command\":\"/help\"}}'")
        print("\nPress CTRL+C to stop the server")
        
        self.app.run(host=host, port=port, debug=debug)


def check_flask_install(io):
    """Check if Flask is installed"""
    try:
        import flask  # noqa: F401
        return True
    except ImportError:
        io.tool_error("Flask is required for API mode")
        io.tool_output("Install with: pip install flask")
        return False


def launch_api(args):
    """Launch the API server"""
    try:
        server = APIServer()
        server.run(debug=False)
    except ImportError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"API server error: {e}")
        return 1


if __name__ == "__main__":
    # For testing
    server = APIServer()
    server.run(debug=True)