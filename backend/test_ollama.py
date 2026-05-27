import asyncio
from langchain_ollama import ChatOllama

async def test_ollama():
    llm = ChatOllama(model="deepseek-r1", base_url="http://127.0.0.1:11434")
    
    count = 0
    async for chunk in llm.astream("Say exactly 'hello'"):
        print(f"Chunk {count}: {chunk.dict()}")
        count += 1
        if count > 5:
            break
            
if __name__ == "__main__":
    asyncio.run(test_ollama())
