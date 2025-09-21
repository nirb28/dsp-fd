# DSP Front Door (dsp-fd)

Enterprise inference system front door that dynamically loads and executes inference modules based on project manifests from the DSP AI Control Tower.

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

Start the front door:
```bash
# Development mode with auto-reload
python start_server.py --dev --reload

# Or production mode
python main.py
```

Run in development mode:
```bash
python start_server.py --dev --reload
```
## Security

- API key authentication via `X-API-Key` header
- Request validation and sanitization
- Secure credential management via environment variables
