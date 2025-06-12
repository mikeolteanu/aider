# Aider Flask API Mode Implementation

## Overview
Implementing a new `--api` mode for aider that launches a Flask API server to accept commands via HTTP endpoints, similar to the existing `--browser` mode but using REST API instead of websockets.

## Requirements
- New `--api` command line flag
- Flask API server with `/command` endpoint
- Handle POST requests with JSON payload: `{'command': '/run ls'}`
- Execute commands and return complete console output
- Handle user input prompts (y/n questions, etc.)
- Single-threaded command execution (queue subsequent requests)
- Return appropriate status codes for busy/ready states

## Architecture

### Core Components
1. **API Server**: Flask application with command endpoint
2. **Command Queue**: Handle single-threaded execution
3. **IO Capture**: Capture all console output during command execution
4. **State Management**: Track if aider is currently executing a command

### API Endpoints
- `POST /command` - Execute aider command
  - Request: `{'command': string}`
  - Response: `{'output': string, 'status': 'completed|error'}` (200)
  - Response: `{'error': 'Command in progress'}` (409 if busy)

### Integration Points
- Modify `args.py` to add `--api` flag
- Update `main.py` to handle API mode initialization
- Create new API module similar to browser mode structure

## Implementation Plan

### Phase 1: Basic Structure ✅
- [x] Add `--api` argument to args.py
- [x] Create basic Flask API module
- [x] Implement command endpoint skeleton
- [x] Add API mode detection in main.py

### Phase 2: Command Execution ✅
- [x] Implement command queue system
- [x] Add IO capture mechanism
- [x] Handle command execution flow
- [x] Add proper error handling

### Phase 3: Advanced Features ✅
- [x] Handle user input prompts
- [x] Add command status tracking
- [x] Implement proper cleanup
- [x] Add comprehensive error handling

### Phase 4: Testing & Polish
- [ ] Add unit tests
- [ ] Test various command scenarios
- [x] Document API usage (OpenAPI spec created)
- [ ] Integration testing

## Technical Notes

### Similar to Browser Mode
- Study existing browser mode implementation in `gui.py`
- Reuse IO handling patterns where possible
- Similar command processing flow

### Key Challenges
1. **IO Redirection**: Capture all stdout/stderr during command execution
2. **User Input Handling**: Deal with interactive prompts
3. **State Management**: Ensure single-threaded command execution
4. **Error Handling**: Graceful handling of command failures

## Progress Log
- Created implementation documentation
- ✅ Phase 1: Added --api argument, created Flask API module, implemented /command endpoint
- ✅ Phase 2: Implemented command execution, IO capture, error handling
- ✅ Phase 3: Added prompt handling, status tracking, cleanup
- Phase 4: Ready for testing

## Current Status
**Implementation complete!** The Flask API mode is now functional with the following features:

### Implemented Features
- `--api` command line flag to launch API mode
- Flask server with endpoints:
  - `GET /health` - Health check
  - `GET /status` - Command execution status
  - `POST /command` - Execute aider commands
- Single-threaded command execution with proper locking
- IO capture for all command output
- Interactive prompt handling (returns needs_input status)
- Support for both slash commands (/add, /drop, etc.) and chat messages
- Comprehensive error handling

### API Usage Examples
```bash
# Start the API server
aider --api

# Health check
curl http://127.0.0.1:5000/health

# Check status
curl http://127.0.0.1:5000/status

# Execute commands
curl -X POST http://127.0.0.1:5000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"/help"}'

curl -X POST http://127.0.0.1:5000/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"add a hello world function"}'
```

### Response Format
```json
{
  "output": "Command output text",
  "status": "completed|error|needs_input"
}
```

For prompts:
```json
{
  "output": "Output so far",
  "status": "needs_input", 
  "prompt": {
    "question": "Create new file?",
    "default": "y",
    "type": "confirmation"
  }
}
```

## OpenAPI Documentation

A complete OpenAPI 3.0.3 specification has been created in `openapi.yaml` that documents:

- All API endpoints with detailed descriptions
- Request/response schemas and examples
- Error handling and status codes
- Command types (slash commands vs chat messages)
- Interactive prompt handling
- Getting started guide

### Using the OpenAPI Spec

You can use the OpenAPI specification to:

1. **Generate client libraries** in various programming languages
2. **Test the API** using tools like Swagger UI or Postman
3. **Understand the API** with comprehensive documentation
4. **Validate requests/responses** in your applications

### View Documentation

You can view the API documentation by:

1. Loading `openapi.yaml` in Swagger Editor: https://editor.swagger.io/
2. Using tools like Redoc or Swagger UI
3. Importing into Postman for testing

### Key OpenAPI Features

- **Complete endpoint documentation** with examples
- **Schema definitions** for all request/response types
- **Error response documentation** with status codes
- **Interactive prompt handling** specifications
- **Command examples** for both slash commands and chat messages