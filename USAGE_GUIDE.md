# DSP Front Door Usage Guide

The DSP Front Door is an enterprise inference system that dynamically loads and executes inference modules based on project manifests from the DSP AI Control Tower.

## API Usage

### Authentication

If `FD_API_KEY` is configured, include it in requests:

```bash
# Using X-API-Key header
curl -H "X-API-Key: your-fd-api-key" http://localhost:8000/health

# Using Authorization header
curl -H "Authorization: Bearer your-fd-api-key" http://localhost:8000/health
```

#### Execute Inference
```bash
curl -X POST http://localhost:8000/inference \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "ai-customer-service",
    "messages": [
      {"role": "user", "content": "What is artificial intelligence?"}
    ],
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 500
    }
  }'
```

## Project Configuration

Projects must have an `inference_endpoint` module in their manifest:

```json
{
  "project_id": "my-project",
  "modules": [
    {
      "module_type": "inference_endpoint",
      "name": "llm-inference",
      "status": "enabled",
      "config": {
        "model_name": "gpt-4",
        "endpoint_url": "https://api.openai.com/v1/chat/completions",
        "system_prompt": "You are a helpful assistant.",
        "max_tokens": 500,
        "temperature": 0.7,
        "top_p": 0.9
      }
    }
  ]
}
```

## Supported Models

### OpenAI Models
- `gpt-4`
- `gpt-4-turbo-preview`
- `gpt-3.5-turbo`
- Custom OpenAI-compatible endpoints

## Python Client Usage

```python
import asyncio
import httpx

async def inference_example():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/inference",
            json={
                "project_id": "ai-customer-service",
                "messages": [
                    {"role": "user", "content": "Hello, I need help with my account."}
                ],
                "parameters": {
                    "temperature": 0.5,
                    "max_tokens": 300
                }
            },
            headers={"X-API-Key": "your-api-key"}  # If authentication enabled
        )
        
        result = response.json()
        print(f"Response: {result['response']}")
        print(f"Model: {result['model_used']}")
        print(f"Processing Time: {result['processing_time_ms']}ms")

# Run the example
asyncio.run(inference_example())
```

## Error Handling

The API returns structured error responses:

```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": [...],
  "timestamp": "2025-09-20T11:13:11-04:00"
}
```

### Common Error Codes
- `400`: Bad Request (validation errors, missing parameters)
- `401`: Unauthorized (invalid API key)
- `404`: Not Found (project not found)
- `500`: Internal Server Error (module loading, inference failures)

## Monitoring and Observability

### Logging
The system uses structured logging with JSON output in production:

```cv json
{
  "event": "Inference completed successfully",
  "project_id": "ai-customer-service",
  "model": "gpt-4",
  "processing_time_ms": 1250.5,
  "timestamp": "2025-09-20T11:13:11-04:00"
}
```

### Metrics
Response headers include processing time:
```
X-Processing-Time-Ms: 1250.5
```

### Health Checks
- `/health`: Basic service health
- `/status`: Detailed system status
- `/projects/{id}/health`: Project-specific health

## Advanced Features

### Multi-turn Conversations
```json
{
  "project_id": "ai-customer-service",
  "messages": [
    {"role": "user", "content": "I can't log in to my account."},
    {"role": "assistant", "content": "I can help with that. What error message are you seeing?"},
    {"role": "user", "content": "It says 'Invalid credentials' but I'm sure my password is correct."}
  ]
}
```

### Additional Context
```json
{
  "project_id": "ai-customer-service",
  "messages": [
    {"role": "user", "content": "How do I reset my password?"}
  ],
  "context": "User account: premium tier, last login: 2025-09-19"
}
```

### Custom Parameters
```json
{
  "project_id": "ai-customer-service",
  "messages": [...],
  "parameters": {
    "model": "gpt-4-turbo-preview",  // Override manifest model
    "temperature": 0.1,              // More focused responses
    "max_tokens": 150,               // Shorter responses
    "top_p": 0.95
  }
}
```

## Troubleshooting

### Common Issues

1. **"Project not found"**
   - Ensure project exists in Control Tower
   - Check project ID spelling
   - Verify Control Tower connectivity

2. **"Module health check failed"**
   - Verify OpenAI API key is valid
   - Check network connectivity to OpenAI
   - Ensure sufficient API quota

3. **"Control Tower connection failed"**
   - Verify Control Tower is running
   - Check `CONTROL_TOWER_BASE_URL` configuration
   - Verify superuser key is correct

4. **Authentication errors**
   - Check `FD_API_KEY` configuration
   - Ensure API key is included in requests
   - Verify header format

### Debug Mode

Start with debug logging:
```bash
python start_server.py --dev --log-level DEBUG
```

### Cache Management

Clear caches if configurations change:
```bash
curl -X DELETE http://localhost:8000/cache
```

## Production Deployment

### Docker Deployment
```bash
# Build and run with docker-compose
docker-compose up -d

# Scale for high availability
docker-compose up -d --scale dsp-fd=3
```

### Environment Variables
```bash
# Production configuration
export CONTROL_TOWER_BASE_URL=https://control-tower.company.com
export CONTROL_TOWER_SUPERUSER_KEY=secure-production-key
export OPENAI_API_KEY=your-production-api-key
export FD_API_KEY=secure-frontend-api-key
export FD_LOG_LEVEL=INFO
```

### Security Considerations
1. Use strong API keys
2. Enable HTTPS in production
3. Configure proper CORS origins
4. Set up monitoring and alerting
5. Regular security updates

## Support

- API Documentation: `http://localhost:8000/docs`
- System Status: `http://localhost:8000/status`
- Health Check: `http://localhost:8000/health`
