# DSP Front Door (dsp-fd)

Enterprise inference system front door that dynamically loads and executes inference modules based on project manifests from the DSP AI Control Tower.

## Features

- **Dynamic Module Loading**: Loads inference modules based on manifest configuration
- **OpenAI Integration**: Built-in support for OpenAI GPT models
- **Manifest-Driven**: Fetches configuration from DSP AI Control Tower
- **Extensible Architecture**: Easy to add new inference providers
- **Security**: API key authentication and request validation
- **Observability**: Structured logging and error handling

## Architecture

```
Request → Front Door → Manifest Fetch → Module Loading → Inference Execution → Response
```

1. **Request Reception**: FastAPI receives inference requests
2. **Manifest Retrieval**: Fetches project manifest from Control Tower
3. **Module Loading**: Dynamically loads appropriate inference module
4. **Execution**: Executes inference with OpenAI or other providers
5. **Response**: Returns structured response with results

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Test installation (optional but recommended):
```bash
python test_startup.py
```

4. Start the front door:
```bash
# Development mode with auto-reload
python start_server.py --dev --reload

# Or production mode
python main.py
```

## API Endpoints

### POST /inference
Execute inference for a project
- **project_id**: Project identifier from manifest
- **messages**: Chat messages for inference
- **parameters**: Optional inference parameters

### GET /health
Health check endpoint

### GET /projects/{project_id}/manifest
Get manifest for a project (cached)

## Configuration

The front door fetches configuration from manifests stored in the DSP AI Control Tower. Inference modules are loaded based on the `inference_endpoint` module configuration in the manifest.

### Supported Inference Providers
- OpenAI GPT models (gpt-4, gpt-3.5-turbo, etc.)
- Extensible to other providers

## Development

Run in development mode:
```bash
python start_server.py --dev --reload
```

## Troubleshooting

### Import Errors
If you encounter import or syntax errors:

1. **Test imports first:**
```bash
python test_imports.py
```

2. **Run startup test:**
```bash
python test_startup.py
```

3. **Common issues:**
   - **Circular imports**: Fixed by using `TYPE_CHECKING` for type hints
   - **Missing dependencies**: Run `pip install -r requirements.txt`
   - **Python path issues**: Run from the project root directory

### Server Startup Issues
- **"invalid syntax"**: Usually indicates import issues - run the test scripts above
- **Configuration errors**: Check your `.env` file has all required values
- **Port conflicts**: Change `FD_PORT` in your `.env` file

## Security

- API key authentication via `X-API-Key` header
- Request validation and sanitization
- Secure credential management via environment variables
