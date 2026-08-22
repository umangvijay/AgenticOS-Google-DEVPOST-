import pytest
import math
from backend.repositories.memory_repository import InMemoryMemoryRepository
from backend.services.embedding_service import MockEmbeddingService

def test_mock_embedding_service():
    service = MockEmbeddingService()
    embedding = service.embed_text("Test query")
    
    assert len(embedding) == 768
    assert embedding[0] == 0.1

def test_in_memory_repository_search():
    repo = InMemoryMemoryRepository()
    
    # User 1 memory
    repo.store_memory(
        user_id="user1",
        content="I have a dog named Max",
        metadata={},
        embedding=[1.0, 0.0, 0.0]
    )
    
    # Another user 1 memory (more relevant to 'cat')
    repo.store_memory(
        user_id="user1",
        content="I have a cat named Whiskers",
        metadata={},
        embedding=[0.0, 1.0, 0.0]
    )
    
    # User 2 memory (should be excluded)
    repo.store_memory(
        user_id="user2",
        content="My cat is named Whiskers too",
        metadata={},
        embedding=[0.0, 1.0, 0.0]
    )
    
    # Query embedding exactly matching the cat memory
    query_embedding = [0.0, 1.0, 0.0]
    
    results = repo.search_memory("user1", query_embedding, limit=2)
    
    assert len(results) == 2
    
    # First result should be the cat memory
    assert results[0].entry.content == "I have a cat named Whiskers"
    assert math.isclose(results[0].similarity_score, 1.0)
    
    # Second result should be the dog memory (0 similarity)
    assert results[1].entry.content == "I have a dog named Max"
    assert math.isclose(results[1].similarity_score, 0.0)

def test_search_memory_limits():
    repo = InMemoryMemoryRepository()
    for i in range(10):
        repo.store_memory("user1", f"Memory {i}", {}, [1.0, 1.0, 1.0])
        
    results = repo.search_memory("user1", [1.0, 1.0, 1.0], limit=5)
    assert len(results) == 5

@pytest.mark.asyncio
async def test_orchestrator_memory_tools():
    from backend.agents.orchestrator.orchestrator_agent import get_orchestrator_agent
    
    repo = InMemoryMemoryRepository()
    service = MockEmbeddingService()
    
    # Initialize agent with memory dependencies
    agent = get_orchestrator_agent(memory_repo=repo, embedding_service=service, user_id="test_user")
    
    # Extract the tools
    tools_dict = {t.__name__: t for t in agent.tools}
    
    assert "search_memory" in tools_dict
    assert "store_memory" in tools_dict
    
    # Call store_memory tool
    store_result = await tools_dict["store_memory"](content="I love Paris", metadata_json='{"category": "preference"}')
    assert "Memory stored successfully" in store_result
    
    # Validate it hit the repository
    assert len(repo._store) == 1
    assert repo._store[0].content == "I love Paris"
    assert repo._store[0].metadata["category"] == "preference"
    
    # Call search_memory tool
    search_result = await tools_dict["search_memory"](query="Paris", limit=5)
    assert "I love Paris" in search_result
