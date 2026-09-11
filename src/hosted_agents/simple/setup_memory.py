"""One-time: create the Foundry Memory store the agent reads/writes.

Run after `azd provision` (needs the chat + embedding deployments):
    FOUNDRY_PROJECT_ENDPOINT=... python setup_memory.py
"""
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MemoryStoreDefaultDefinition, MemoryStoreDefaultOptions
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=DefaultAzureCredential()
)
name = os.environ.get("MEMORY_STORE_NAME", "demo-memory")

try:
    project.beta.memory_stores.get(name)
    print(f"Memory store '{name}' already exists")
except ResourceNotFoundError:
    project.beta.memory_stores.create(
        name=name,
        description="Long-term memory for the LangGraph demo agent",
        definition=MemoryStoreDefaultDefinition(
            chat_model=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini"),
            embedding_model=os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
            options=MemoryStoreDefaultOptions(user_profile_enabled=True, chat_summary_enabled=True),
        ),
    )
    print(f"Memory store '{name}' created")
