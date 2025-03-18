from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    logger.info("Starting price comparison task...")
    try:
        agent = Agent(
            task="Check the price of gpt-4o",
            llm=ChatOpenAI(model="gpt-4o"),
        )
        logger.info("Agent created successfully")
        
        await agent.run()
        logger.info("Price check completed successfully")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())