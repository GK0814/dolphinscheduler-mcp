import asyncio
import os
import pytest
from src.dolphinscheduler_mcp.client import DolphinSchedulerClient

pytestmark = pytest.mark.skipif(
    os.environ.get("DS_MCP_RUN_INTEGRATION_TESTS") != "1",
    reason="Integration test creates a real DolphinScheduler project.",
)

async def test_create_project():
    # Create a client with environment variables
    client = DolphinSchedulerClient(
        api_url=os.environ.get("DOLPHINSCHEDULER_API_URL"),
        api_key=os.environ.get("DOLPHINSCHEDULER_API_KEY")
    )
    
    try:
        # Call the create_project method
        project_name = "mcp-demo1"
        description = "MCP Demo Project"
        
        print(f"Creating project {project_name}...")
        response = await client.request(
            "POST", 
            "projects", 
            params={
                "projectName": project_name, 
                "description": description
            }
        )
        
        print("Response:")
        print(response)
        
    finally:
        # Close the client
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_create_project())
