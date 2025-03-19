from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserContextConfig
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.agent.views import AgentHistoryList, AgentHistory
import asyncio
import logging
from dotenv import load_dotenv
from datetime import datetime
import os
from pathlib import Path
import base64
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Configure logging to see detailed output
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Enable browser-use package logging
logging.getLogger('browser_use').setLevel(logging.DEBUG)

load_dotenv()

async def main(task: str):
    print("Starting browser-use agent...")

    base_dir = "videos"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_dir = os.path.join(base_dir, f"{timestamp}")

    browser = Browser(
        config=BrowserConfig(
            headless=True
        )
    )

    config = BrowserContextConfig(
        save_recording_path=os.path.join(base_dir, "recording"),
        save_downloads_path=os.path.join(base_dir, "download"),
        trace_path=os.path.join(base_dir, "trace"),
    )

    context = BrowserContext(browser=browser, config=config)

    try:
        agent = Agent(
            task=task,
            llm=ChatOpenAI(model="gpt-4o"),
            browser_context=context,
            save_conversation_path=os.path.join(base_dir, "conversation"),
            generate_gif=os.path.join(base_dir, "screenshots.gif"),
        )

        print("Agent initialized, starting execution...")
        result = await agent.run()

        snapshot_files = save_snapshots(result.history, os.path.join(base_dir, "snapshots"))
        print(f"Saved {len(snapshot_files)} snapshots")

        print("Agent execution completed!")
        print("Result:", result)
    finally:
        await browser.close()  # Ensure browser is closed even if there's an error

def save_snapshots(history: list[AgentHistory], output_dir: str = "snapshots") -> list[str]:
    """
    Save all screenshots from the agent's history as separate PNG files.
    
    Args:
        history: List of AgentHistory items containing screenshots
        output_dir: Directory where snapshots will be saved
        
    Returns:
        List of paths to saved snapshot files
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    
    # Iterate through history directly
    for i, history_item in enumerate(history):
        if history_item.state.screenshot:  # Check if screenshot exists
            # Create filename with step number
            filename = f"snapshot_{i+1:03d}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Decode and save the screenshot
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(history_item.state.screenshot))
            
            saved_files.append(filepath)
            
    return saved_files

# asyncio.run(main())

class TaskRequest(BaseModel):
    task: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/run")
async def run(request: TaskRequest):
    result = await main(request.task)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)