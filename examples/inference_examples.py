"""
Example usage of the DSP Front Door inference system.
"""

import asyncio
import json
import httpx
from typing import Dict, Any, List


class DSPFrontDoorClient:
    """Simple client for DSP Front Door API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
        self.timeout = 60.0
    
    async def infer(
        self, 
        project_id: str, 
        messages: List[Dict[str, str]], 
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute inference request."""
        request_data = {
            "project_id": project_id,
            "messages": messages
        }
        
        if parameters:
            request_data["parameters"] = parameters
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/inference",
                headers=self.headers,
                json=request_data
            )
            response.raise_for_status()
            return response.json()
    
    async def get_manifest(self, project_id: str) -> Dict[str, Any]:
        """Get project manifest."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/projects/{project_id}/manifest",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_projects(self) -> Dict[str, Any]:
        """List available projects."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/projects",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


async def example_simple_chat():
    """Example: Simple chat inference."""
    print("=== Example 1: Simple Chat ===")
    
    client = DSPFrontDoorClient()
    
    messages = [
        {"role": "user", "content": "What is artificial intelligence?"}
    ]
    
    try:
        result = await client.infer("ai-customer-service", messages)
        
        print(f"Model Used: {result['model_used']}")
        print(f"Processing Time: {result['processing_time_ms']:.2f}ms")
        print(f"Tokens Used: {result.get('tokens_used', 'N/A')}")
        print(f"Response: {result['response']}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_conversation_context():
    """Example: Multi-turn conversation with context."""
    print("\n=== Example 2: Multi-turn Conversation ===")
    
    client = DSPFrontDoorClient()
    
    messages = [
        {"role": "user", "content": "I'm having trouble with my account login."},
        {"role": "assistant", "content": "I'd be happy to help you with your login issue. Can you describe what happens when you try to log in?"},
        {"role": "user", "content": "I get an error saying 'Invalid credentials' even though I'm sure my password is correct."}
    ]
    
    # Add custom parameters
    parameters = {
        "temperature": 0.5,  # More focused responses for support
        "max_tokens": 300
    }
    
    try:
        result = await client.infer("ai-customer-service", messages, parameters)
        
        print(f"Model Used: {result['model_used']}")
        print(f"Processing Time: {result['processing_time_ms']:.2f}ms")
        print(f"Response: {result['response']}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_with_context():
    """Example: Inference with additional context."""
    print("\n=== Example 3: Inference with Context ===")
    
    client = DSPFrontDoorClient()
    
    messages = [
        {"role": "user", "content": "How do I reset my password?"}
    ]
    
    # Additional context that could come from RAG or knowledge base
    context = """
    Password Reset Policy:
    - Users can reset passwords using email verification
    - Must include special characters and be 8+ characters
    - Password history: cannot reuse last 3 passwords
    - Account locks after 3 failed attempts
    """
    
    request_data = {
        "project_id": "ai-customer-service",
        "messages": messages,
        "context": context,
        "parameters": {
            "temperature": 0.3,
            "max_tokens": 250
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            response = await http_client.post(
                "http://localhost:8000/inference",
                headers={"Content-Type": "application/json"},
                json=request_data
            )
            response.raise_for_status()
            result = response.json()
        
        print(f"Model Used: {result['model_used']}")
        print(f"Processing Time: {result['processing_time_ms']:.2f}ms")
        print(f"Response: {result['response']}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_project_exploration():
    """Example: Explore available projects and their configurations."""
    print("\n=== Example 4: Project Exploration ===")
    
    client = DSPFrontDoorClient()
    
    try:
        # List all projects
        projects = await client.list_projects()
        manifests = projects.get("manifests", [])
        
        print(f"Available Projects: {len(manifests)}")
        
        for manifest in manifests[:3]:  # Show first 3
            project_id = manifest.get("project_id")
            name = manifest.get("project_name")
            print(f"- {project_id}: {name}")
            
            # Get detailed manifest
            detailed = await client.get_manifest(project_id)
            
            # Find inference module
            inference_modules = [
                m for m in detailed.get("modules", [])
                if m.get("module_type") == "inference_endpoint"
            ]
            
            if inference_modules:
                module = inference_modules[0]
                config = module.get("config", {})
                print(f"  Model: {config.get('model_name', 'Unknown')}")
                print(f"  Status: {module.get('status', 'Unknown')}")
                print(f"  Max Tokens: {config.get('max_tokens', 'Not set')}")
            
    except Exception as e:
        print(f"Error: {e}")


async def example_batch_processing():
    """Example: Process multiple requests in parallel."""
    print("\n=== Example 5: Batch Processing ===")
    
    client = DSPFrontDoorClient()
    
    requests = [
        {
            "messages": [{"role": "user", "content": "What are your business hours?"}],
            "parameters": {"temperature": 0.3}
        },
        {
            "messages": [{"role": "user", "content": "How do I cancel my subscription?"}],
            "parameters": {"temperature": 0.3}
        },
        {
            "messages": [{"role": "user", "content": "What payment methods do you accept?"}],
            "parameters": {"temperature": 0.3}
        }
    ]
    
    try:
        # Process all requests in parallel
        tasks = [
            client.infer("ai-customer-service", req["messages"], req["parameters"])
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Request {i+1} failed: {result}")
            else:
                print(f"Request {i+1}:")
                print(f"  Processing Time: {result['processing_time_ms']:.2f}ms")
                print(f"  Response: {result['response'][:100]}...")
                
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples."""
    print("DSP Front Door Inference Examples")
    print("=" * 40)
    
    # Note: Make sure DSP Front Door and Control Tower are running
    print("Prerequisites:")
    print("1. DSP Control Tower running on http://localhost:5000")
    print("2. DSP Front Door running on http://localhost:8000")
    print("3. Project 'ai-customer-service' exists in Control Tower")
    print("4. OpenAI API key configured")
    print()
    
    examples = [
        example_simple_chat,
        example_conversation_context,
        example_with_context,
        example_project_exploration,
        example_batch_processing
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Brief pause between examples
        except KeyboardInterrupt:
            print("\nStopped by user")
            break
        except Exception as e:
            print(f"Example failed: {e}")
            continue
    
    print("\n" + "=" * 40)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
