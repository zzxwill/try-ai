from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import logging
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def start_recording_browser(output_dir):
    """Start a separate browser just for recording what happens on screen"""
    logger.info("Starting recording browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            '--start-maximized',  # Start maximized
            '--window-size=1920,1080',  # Set window size
            '--no-sandbox',  # Required in Docker
            '--disable-setuid-sandbox',  # Required in Docker
        ]
    )
    
    # Create context with recording enabled
    context = await browser.new_context(
        record_video_dir=output_dir,
        record_video_size={"width": 1920, "height": 1080},
        viewport={"width": 1920, "height": 1080}
    )
    
    # Create a page that will be used for recording
    page = await context.new_page()
    
    # Set page to be in front
    await page.bring_to_front()
    
    # Go to a blank page initially
    await page.goto('about:blank')
    
    logger.info("Recording browser started")
    return playwright, browser, context, page

async def main():
    # Set up recording directory
    videos_dir = "videos"
    os.makedirs(videos_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    recording_dir = os.path.join(videos_dir, f"recording-{timestamp}")
    os.makedirs(recording_dir, exist_ok=True)
    
    logger.info(f"Recording directory: {recording_dir}")
    
    # Variables to store Playwright instances
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        # Start recording browser before creating the agent
        playwright, browser, context, page = await start_recording_browser(recording_dir)
        
        # Run the agent
        logger.info("Starting price comparison task...")
        agent = Agent(
            task="Check the price of gpt-4o",
            llm=ChatOpenAI(model="gpt-4o"),
        )
        logger.info("Agent created successfully")
        
        # Run the agent's task
        await agent.run()
        logger.info("Price check completed successfully")
        
        # Close the recording browser gracefully to ensure video is saved
        logger.info("Closing recording browser...")
        if page:
            await page.close()
        if context:
            await context.close()  # This ensures videos are saved
        if browser:
            await browser.close()
            
        # Give some time for the video to be finalized
        logger.info("Waiting for video to be finalized...")
        await asyncio.sleep(3)
        
        # Check for recorded videos
        video_files = [f for f in os.listdir(recording_dir) if f.endswith('.webm')]
        if video_files:
            logger.info(f"Videos created: {video_files}")
            for video_file in video_files:
                video_path = os.path.join(recording_dir, video_file)
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
                logger.info(f"Video file: {video_path}, Size: {size_mb:.2f} MB")
        else:
            logger.warning(f"No videos found in {recording_dir}")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    
    finally:
        # Make sure to clean up Playwright resources
        if playwright:
            try:
                await playwright.stop()
                logger.info("Playwright stopped")
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")

if __name__ == "__main__":
    asyncio.run(main())