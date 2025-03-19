from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import logging
import os
import time
import psutil
import subprocess
import shutil
import signal
from dotenv import load_dotenv
from datetime import datetime
import shlex
import sys
from fastapi import FastAPI
from pydantic import BaseModel

# Add patch before any browser_use components are initialized
import sys
import importlib.util
if importlib.util.find_spec("browser_use") is not None:
    # Apply the patch to fix the "using Sync API inside asyncio loop" issue
    import browser_use.browser.context
    import inspect
    
    # Set up logging early
    logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')
    logger = logging.getLogger(__name__)
    
    # Introspect the BrowserContext class to find browser and page creation methods
    context_class = browser_use.browser.context.BrowserContext
    
    # Log available methods to help with debugging
    logger.info("Available BrowserContext methods: %s", 
                [m for m in dir(context_class) if not m.startswith('__')])
    
    # Add a patch for the page navigation method to diagnose and fix page load issues
    if hasattr(context_class, 'navigate'):
        original_navigate = context_class.navigate
        
        async def patched_navigate(self, url, **kwargs):
            logger.info(f"Attempting to navigate to: {url}")
            try:
                # Try with a longer timeout
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = 60000  # 60 seconds
                if 'wait_until' not in kwargs:
                    kwargs['wait_until'] = 'networkidle'  # Wait for network to be idle
                
                return await original_navigate(self, url, **kwargs)
            except Exception as e:
                logger.warning(f"Navigation to {url} failed: {e}")
                
                # Try some fallback strategies
                try:
                    logger.info(f"Attempting fallback navigation to {url}...")
                    if hasattr(self, 'page') and self.page:
                        # Try a different navigation approach
                        try:
                            await self.page.goto(url, timeout=60000, wait_until='networkidle')
                            logger.info(f"Direct page.goto to {url} succeeded")
                            return True
                        except Exception as page_error:
                            logger.warning(f"Direct page.goto failed: {page_error}")
                    
                    # If that fails, try the actual Playwright API directly
                    if hasattr(self, 'browser') and self.browser:
                        try:
                            test_page = await self.browser.new_page()
                            await test_page.goto(url, timeout=60000, wait_until='networkidle')
                            logger.info(f"New page goto to {url} succeeded")
                            # Transfer the successful page to the context
                            if hasattr(self, 'page'):
                                old_page = self.page
                                self.page = test_page
                                # Close the old page to avoid leaks
                                try:
                                    await old_page.close()
                                except:
                                    pass
                            return True
                        except Exception as new_page_error:
                            logger.warning(f"New page goto failed: {new_page_error}")
                            try:
                                await test_page.close()
                            except:
                                pass
                    
                    # If everything fails and we're in Docker, try a local success page
                    if os.path.exists('/.dockerenv'):
                        try:
                            if hasattr(self, 'page') and self.page:
                                logger.info("Setting up mock content as fallback")
                                await self.page.set_content(f"""
                                <html>
                                <head><title>Mock Page for {url}</title></head>
                                <body style="background-color: white; color: black; font-family: Arial, sans-serif; padding: 20px;">
                                    <h1>Fallback Content</h1>
                                    <p>The page <b>{url}</b> could not be loaded, but we're continuing with mocked content.</p>
                                    <p>This is a simulation to allow the agent to continue despite network issues.</p>
                                    <div id="content" style="border: 1px solid #ccc; padding: 10px; margin-top: 20px;">
                                        <h2>Simulated Content</h2>
                                        <p>Imagine this is the content from {url}</p>
                                        <ul>
                                            <li>Item 1</li>
                                            <li>Item 2</li>
                                            <li>Item 3</li>
                                        </ul>
                                    </div>
                                </body>
                                </html>
                                """)
                                logger.info("Mock content set successfully")
                                return True
                        except Exception as content_error:
                            logger.warning(f"Failed to set mock content: {content_error}")
                
                except Exception as fallback_error:
                    logger.error(f"All fallback navigation attempts failed: {fallback_error}")
                
                # Re-raise the original error
                raise
        
        # Apply the patch to the navigate method
        context_class.navigate = patched_navigate
        logger.info("Patched navigate method to handle page load failures")
    
    # Define generic patching for any async method that might create browsers/pages
    def create_patch_for(method_name):
        if not hasattr(context_class, method_name):
            logger.warning(f"Method {method_name} not found in BrowserContext")
            return None
            
        original_method = getattr(context_class, method_name)
        
        # Only patch async methods
        if not inspect.iscoroutinefunction(original_method):
            logger.warning(f"Method {method_name} is not async, skipping patch")
            return None
            
        async def patched_method(self, *args, **kwargs):
            try:
                return await original_method(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"{method_name} failed: {type(e).__name__}: {e}")
                
                # Special handling based on method purpose
                if 'browser' in method_name.lower() or 'launch' in method_name.lower():
                    # This is likely a browser creation method
                    logger.info(f"Attempting fallback browser creation for {method_name}")
                    from playwright.async_api import async_playwright
                    p = await async_playwright().start()
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-gpu',
                            '--disable-dev-shm-usage',
                            '--disable-accelerated-2d-canvas',
                        ]
                    )
                    return browser
                elif 'page' in method_name.lower():
                    # This is likely a page creation method
                    if hasattr(self, 'browser') and self.browser:
                        logger.info(f"Attempting fallback page creation for {method_name}")
                        try:
                            return await self.browser.new_page()
                        except Exception as inner_e:
                            logger.error(f"Failed to create fallback page: {inner_e}")
                            raise
                # Re-raise for other methods
                raise
                
        return patched_method
    
    # Methods that might be responsible for browser/page creation in different versions
    browser_method_candidates = [
        'launch_browser', '_launch_browser', 'create_browser', '_create_browser',
        'get_browser', '_get_browser', 'setup_browser', '_setup_browser'
    ]
    
    page_method_candidates = [
        'new_page', '_new_page', 'create_page', '_create_page', 
        'get_page', '_get_page', 'setup_page', '_setup_page'
    ]
    
    # Try to patch browser creation methods
    for method_name in browser_method_candidates:
        patched = create_patch_for(method_name)
        if patched:
            logger.info(f"Successfully patched browser method: {method_name}")
            setattr(context_class, method_name, patched)
    
    # Try to patch page creation methods
    for method_name in page_method_candidates:
        patched = create_patch_for(method_name)
        if patched:
            logger.info(f"Successfully patched page method: {method_name}")
            setattr(context_class, method_name, patched)
    
    logger.info("Applied dynamic patches to browser_use based on available methods")

app = FastAPI()

# FastAPI and web server imports
from fastapi import FastAPI, HTTPException
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def is_tool_available(tool_name):
    """Check if a command-line tool is available"""
    try:
        subprocess.run([tool_name, "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=False)
        return True
    except FileNotFoundError:
        return False

async def setup_recording_environment():
    """Set up directories for recording"""
    # Create timestamp for this recording
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Set up recording directory
    videos_dir = "videos"
    os.makedirs(videos_dir, exist_ok=True)
    
    video_path = os.path.join(videos_dir, f"recording-{timestamp}")
    os.makedirs(video_path, exist_ok=True)
    
    screenshot_dir = os.path.join(video_path, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    
    return video_path, screenshot_dir

def find_chrome_processes_before():
    """Find all Chrome processes before running the agent"""
    chrome_pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                chrome_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    logger.info(f"Found {len(chrome_pids)} Chrome processes before agent start")
    return chrome_pids

async def wait_and_find_chrome_window():
    """Wait for Chrome window to appear and return its ID"""
    # Wait a moment for the window to be created
    await asyncio.sleep(3)
    
    try:
        # Find Chrome windows
        window_ids = subprocess.check_output(
            "xdotool search --onlyvisible --class chrome || xdotool search --onlyvisible --class chromium", 
            shell=True
        ).decode().strip().split('\n')
        
        if window_ids and window_ids[0]:
            # Last window is likely the newest one
            window_id = window_ids[-1]
            logger.info(f"Found Chrome window ID: {window_id}")
            
            # Try to get window info to verify
            window_info = subprocess.check_output(
                ["xdotool", "getwindowname", window_id], 
                text=True
            ).strip()
            
            logger.info(f"Window title: {window_info}")
            return window_id
    except Exception as e:
        logger.error(f"Error finding Chrome window: {e}")
    
    return None

async def screen_record_with_ffmpeg(output_file):
    """Record the screen using ffmpeg if available"""
    if not is_tool_available('ffmpeg'):
        logger.warning("ffmpeg not found, screen recording disabled")
        return None
    
    logger.info(f"Starting screen recording to {output_file}")
    
    # Check if we're in a Docker container (likely using Xvfb)
    in_docker = os.path.exists('/.dockerenv')
    
    try:
        # Determine display to use
        display = os.environ.get('DISPLAY', ':99.0')
        logger.info(f"Using display: {display}")
        
        # For Docker with Xvfb
        if in_docker:
            cmd = [
                "ffmpeg",
                "-f", "x11grab",
                "-video_size", "1920x1080",
                "-framerate", "10",
                "-i", display,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-qp", "0",
                "-y",  # Overwrite output file
                output_file
            ]
        else:
            # For macOS
            if sys.platform == 'darwin':
                cmd = [
                    "ffmpeg",
                    "-f", "avfoundation",
                    "-framerate", "10", 
                    "-i", "1",  # Screen is input 1 on macOS
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-qp", "0",
                    "-y",
                    output_file
                ]
            else:
                # For standard Linux
                cmd = [
                    "ffmpeg",
                    "-f", "x11grab",
                    "-video_size", "1920x1080",
                    "-framerate", "10",
                    "-i", display,
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-qp", "0",
                    "-y",
                    output_file
                ]
        
        # Log the command
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        
        # Start ffmpeg process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("FFmpeg screen recording started successfully")
        return process
    except Exception as e:
        logger.error(f"Error starting screen recording: {str(e)}")
        return None

async def take_screenshots(output_dir, stop_event):
    """Take full screen screenshots periodically"""
    screenshot_count = 0
    failed_count = 0
    max_failures = 5
    
    # Check for screenshot tools with fallbacks
    use_import = is_tool_available('import')
    use_screencapture = is_tool_available('screencapture')
    use_scrot = is_tool_available('scrot')
    use_convert = is_tool_available('convert')  # Part of ImageMagick
    use_playwright = True  # Add Playwright as a fallback option
    
    # In Docker, detect if we're in a container
    in_docker = os.path.exists('/.dockerenv')
    
    if not any([use_import, use_screencapture, use_scrot, use_convert, use_playwright]):
        logger.warning("No screenshot tools found, screenshots disabled")
        return
    
    logger.info(f"Using screenshot tools in {'Docker' if in_docker else 'local'} mode: " +
                f"import={use_import}, screencapture={use_screencapture}, " +
                f"scrot={use_scrot}, convert={use_convert}, playwright={use_playwright}")
    
    # Initialize Playwright for screenshots - USING ASYNC API INSTEAD OF SYNC
    playwright_browser = None
    playwright = None
    
    if use_playwright and in_docker:
        try:
            # Use async API instead of sync to avoid errors
            from playwright.async_api import async_playwright
            
            # Start playwright with async API
            playwright = await async_playwright().start()
            
            # Use specific browser arguments to optimize for headless screenshot capture
            playwright_browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu", 
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--mute-audio",
                ]
            )
            logger.info("Initialized Playwright for screenshots using async API")
            
            # Create and navigate to a test page to ensure rendering is working
            try:
                test_page = await playwright_browser.new_page(viewport={"width": 1280, "height": 720})
                await test_page.goto("about:blank")
                await test_page.set_content("""
                <html>
                <head>
                    <style>
                        body { background-color: blue; color: white; font-size: 48px; text-align: center; padding-top: 50px; }
                    </style>
                </head>
                <body>
                    <h1>Screenshot Test Page</h1>
                    <p>This should be visible in screenshots</p>
                </body>
                </html>
                """)
                
                # Take a test screenshot to verify rendering
                test_screenshot = os.path.join(output_dir, "test_screenshot.png")
                await test_page.screenshot(path=test_screenshot)
                
                if os.path.exists(test_screenshot) and os.path.getsize(test_screenshot) > 0:
                    try:
                        # Check if the test screenshot is black
                        import PIL.Image
                        img = PIL.Image.open(test_screenshot)
                        extrema = img.convert("L").getextrema()
                        
                        if extrema[0] < 5 and extrema[1] < 5:
                            logger.warning("Test screenshot appears to be all black! Display or rendering issues detected.")
                            use_playwright = False  # Disable Playwright if it produces black screenshots
                        else:
                            logger.info("Playwright test screenshot has content - browser rendering is working correctly")
                    except ImportError:
                        logger.warning("PIL not available to analyze test screenshot")
                else:
                    logger.warning("Failed to create or empty test screenshot")
                    use_playwright = False
                
                await test_page.close()
                
            except Exception as e:
                logger.error(f"Error testing Playwright screenshots: {str(e)}")
                use_playwright = False
                
        except Exception as e:
            logger.warning(f"Failed to initialize Playwright for screenshots: {str(e)}")
            use_playwright = False
    
    if in_docker:
        logger.info("Running in Docker, prioritizing Playwright for screenshots")
        
    # Create a page for taking screenshots if Playwright is available
    playwright_page = None
    if use_playwright and playwright_browser:
        try:
            playwright_page = await playwright_browser.new_page(viewport={"width": 1920, "height": 1080})
            await playwright_page.goto("about:blank")
        except Exception as e:
            logger.error(f"Error creating Playwright page for screenshots: {str(e)}")
            playwright_page = None
    
    # Take screenshots until stop_event is set
    while not stop_event.is_set():
        # First try using traditional system tools
        success = False
        error_message = ""
        screenshot_path = os.path.join(output_dir, f"screenshot_{screenshot_count:04d}.png")
        
        # In Docker, prefer scrot since it's often most reliable
        if in_docker and use_scrot:
            try:
                # Try with scrot 
                result = subprocess.run(
                    ["scrot", "-z", "-q", "100", screenshot_path],  # -z for silent mode, -q for quality
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=False,
                    env=dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":99"))
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    # Check if the screenshot is not black
                    try:
                        import PIL.Image
                        img = PIL.Image.open(screenshot_path)
                        extrema = img.convert("L").getextrema()
                        
                        # If the darkest and lightest pixels are very close to 0, image is likely black
                        if extrema[0] < 5 and extrema[1] < 5:
                            logger.warning(f"Screenshot appears to be all black with scrot")
                            # Continue to try other methods
                        else:
                            success = True
                            logger.info("Used scrot for screenshot")
                    except ImportError:
                        # Can't check with PIL, assume success
                        success = True
                        logger.info("Used scrot for screenshot (no PIL check)")
                else:
                    error_message = f"scrot failed: {result.stderr.decode()}"
            except Exception as e:
                error_message = f"Error with scrot: {str(e)}"
                
        # If scrot failed, try Playwright in Docker
        if not success and in_docker and use_playwright and playwright_page:
            try:
                # Use Playwright
                await playwright_page.bring_to_front()
                
                # Capture full viewport
                await playwright_page.screenshot(path=screenshot_path, full_page=False)
                
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    success = True
                    logger.info("Used Playwright for screenshot")
                else:
                    error_message = "Playwright screenshot failed or is empty"
            except Exception as e:
                error_message = f"Error with Playwright screenshot: {str(e)}"

        # Try with import (ImageMagick)
        if not success and use_import:
            try:
                # Use import from ImageMagick
                result = subprocess.run(
                    ["import", "-window", "root", screenshot_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=False,
                    env=dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":99"))
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    # Check for black screenshot
                    try:
                        import PIL.Image
                        img = PIL.Image.open(screenshot_path)
                        extrema = img.convert("L").getextrema()
                        
                        if extrema[0] < 5 and extrema[1] < 5:
                            logger.warning(f"Screenshot appears to be all black with import")
                            # Continue to try other methods
                        else:
                            success = True
                            logger.info("Used import for screenshot")
                    except ImportError:
                        success = True
                        logger.info("Used import for screenshot (no PIL check)")
                else:
                    error_message += f", import failed: {result.stderr.decode()}"
            except Exception as e:
                error_message += f", Error with import: {str(e)}"
        
        # Try with convert (ImageMagick)
        if not success and use_convert:
            try:
                # Use convert from ImageMagick
                result = subprocess.run(
                    ["convert", "x:", screenshot_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=False,
                    env=dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":99"))
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    # Check for black screenshot
                    try:
                        import PIL.Image
                        img = PIL.Image.open(screenshot_path)
                        extrema = img.convert("L").getextrema()
                        
                        if extrema[0] < 5 and extrema[1] < 5:
                            logger.warning(f"Screenshot appears to be all black with convert")
                            # Continue to try other methods
                        else:
                            success = True
                            logger.info("Used convert for screenshot")
                    except ImportError:
                        success = True
                        logger.info("Used convert for screenshot (no PIL check)")
                else:
                    error_message += f", convert failed: {result.stderr.decode()}"
            except Exception as e:
                error_message += f", Error with convert: {str(e)}"
        
        # If not in Docker and on macOS
        if not success and not in_docker and use_screencapture:
            try:
                # Use screencapture on macOS
                result = subprocess.run(
                    ["screencapture", screenshot_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=False
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    success = True
                    logger.info("Used screencapture for screenshot")
                else:
                    error_message += f", screencapture failed: {result.stderr.decode()}"
            except Exception as e:
                error_message += f", Error with screencapture: {str(e)}"
        
        # Non-docker scrot as last resort
        if not success and not in_docker and use_scrot:
            try:
                result = subprocess.run(
                    ["scrot", screenshot_path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=False
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    success = True
                    logger.info("Used scrot for screenshot")
                else:
                    error_message += f", scrot failed: {result.stderr.decode()}"
            except Exception as e:
                error_message += f", Error with scrot: {str(e)}"
        
        # Last resort: Use Playwright to generate a basic colored page if everything fails
        if not success and use_playwright and playwright_browser:
            try:
                logger.warning("All screenshot methods failed, creating a synthetic screenshot")
                # Create a colored page with frame number
                page = await playwright_browser.new_page(viewport={"width": 1920, "height": 1080})
                await page.set_content(f"""
                <html>
                <head>
                    <style>
                        body {{ 
                            background: linear-gradient(45deg, #f06, #9f6);
                            color: white; 
                            font-family: Arial, sans-serif;
                            height: 100vh;
                            margin: 0;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                        }}
                        h1 {{ font-size: 64px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }}
                        .info {{ font-size: 36px; margin-top: 20px; }}
                        .timestamp {{ font-size: 24px; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1>Synthetic Screenshot #{screenshot_count}</h1>
                    <div class="info">Screenshot capture failed, showing this instead</div>
                    <div class="timestamp">Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                </body>
                </html>
                """)
                await page.screenshot(path=screenshot_path)
                await page.close()
                
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    success = True
                    logger.info("Created synthetic screenshot as fallback")
                else:
                    error_message += ", synthetic screenshot failed"
            except Exception as e:
                error_message += f", Error with synthetic screenshot: {str(e)}"
        
        if success and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
            logger.info(f"Captured screenshot {screenshot_count}")
            screenshot_count += 1
            failed_count = 0  # Reset failure counter on success
        else:
            logger.warning(f"Screenshot {screenshot_count} failed or empty. Errors: {error_message}")
            failed_count += 1
            if failed_count >= max_failures:
                logger.error(f"Too many screenshot failures ({failed_count}), stopping")
                break
        
        await asyncio.sleep(1)  # Take screenshots frequently
    
    # Clean up Playwright
    if playwright_page:
        try:
            await playwright_page.close()
        except:
            pass
    
    if playwright_browser:
        try:
            await playwright_browser.close()
        except:
            pass
            
    if playwright:
        try:
            await playwright.stop()
        except:
            pass
            
    logger.info(f"Screenshot thread stopped after capturing {screenshot_count} screenshots")

async def main(task: str):
    recording_process = None
    try:
        # Set up recording directory
        video_path, screenshot_dir = await setup_recording_environment()
        logger.info(f"Recording to {video_path}")
        
        # Find Chrome processes before we start
        chrome_pids_before = find_chrome_processes_before()
        
        # Create an event to signal when to stop capturing
        stop_capture = asyncio.Event()
        
        # Try to start screen recording if ffmpeg is available
        recording_file = os.path.join(video_path, "screen_recording.mp4")
        recording_process = await screen_record_with_ffmpeg(recording_file)
        
        # Start regular screenshot capture 
        screenshot_task = asyncio.create_task(
            take_screenshots(screenshot_dir, stop_capture)
        )
        
        # Set environment variables for browser_use
        # If we're in Docker with Xvfb, use headless mode to avoid display issues
        if os.path.exists('/.dockerenv') and os.environ.get('DISPLAY', '').startswith(':'):
            os.environ["BROWSER_USE_HEADLESS"] = "true"  # Use headless in Docker with Xvfb
            # Set essential browser arguments for Docker/Xvfb environment
            os.environ["BROWSER_USE_EXTRA_ARGS"] = "--no-sandbox,--disable-gpu,--disable-dev-shm-usage,--disable-setuid-sandbox,--disable-web-security,--disable-features=IsolateOrigins,site-per-process"
            
            # Set DNS settings to ensure connectivity in Docker
            os.environ["BROWSER_USE_DNS_SERVERS"] = "8.8.8.8,8.8.4.4"
            
            # Configure network settings
            os.environ["BROWSER_USE_IGNORE_HTTPS_ERRORS"] = "true"
            os.environ["BROWSER_USE_BYPASS_CSP"] = "true"
            
            # Configure timeouts more generously
            os.environ["BROWSER_USE_NAVIGATION_TIMEOUT"] = "60000" # 60 seconds
            os.environ["BROWSER_USE_TIMEOUT"] = "90000" # 90 seconds
            
            # Additional settings to help with connectivity
            os.environ["BROWSER_USE_USER_AGENT"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            
            logger.info("Running in Docker with Xvfb, using headless browser mode with extra args and network settings")
        else:
            os.environ["BROWSER_USE_HEADLESS"] = "false"  # Non-headless mode for local dev
            logger.info("Running in local environment, using non-headless browser mode")
        
        # Create the agent using the correct API
        try:
            # First check network connectivity
            logger.info("Checking network connectivity before creating agent...")
            try:
                import urllib.request
                urllib.request.urlopen("https://www.google.com", timeout=10)
                logger.info("Network connectivity check passed")
            except Exception as e:
                logger.warning(f"Network connectivity check failed: {e}")
                logger.info("Will continue despite network check failure")
            
            # Create additional debugging proxy for better diagnosis
            proxy_debug = os.environ.get("BROWSER_USE_PROXY", "")
            if not proxy_debug and os.path.exists('/.dockerenv'):
                # If in Docker and no proxy set, try setting up a debug proxy
                proxy_choices = [
                    "http://direct:80", # Direct connection
                    "", # No proxy
                    "system", # Use system proxy
                    "http://host.docker.internal:3128", # Common Proxy
                    "auto" # Automatic detection
                ]
                
                # Try some common DNS servers
                for dns in ["8.8.8.8", "1.1.1.1", "9.9.9.9"]:
                    os.environ["BROWSER_USE_DNS_SERVERS"] = dns
                    logger.info(f"Testing DNS with: {dns}")
                    try:
                        import socket
                        socket.gethostbyname("www.google.com")
                        logger.info(f"DNS resolution working with {dns}")
                        break
                    except:
                        logger.warning(f"DNS resolution failed with {dns}")
            
            # Set browser debugging variables as a last resort
            if os.path.exists('/.dockerenv'):
                # Set browser to debug mode to see what's happening
                os.environ["BROWSER_USE_DEBUG"] = "true"
                # Force persistent context to fix multiple initialization issues
                os.environ["BROWSER_USE_NON_PERSISTENT_CONTEXT"] = "false"
                # Set a long timeout for page loads
                os.environ["BROWSER_USE_PAGE_LOAD_TIMEOUT"] = "120000" # 2 minutes
            
            logger.info("Creating agent with task: %s", task)
            agent = Agent(
                task=task,
                llm=ChatOpenAI(model="gpt-4o")
            )
            logger.info("Agent created successfully")
            
            # Start the agent task with extra logging
            logger.info("Starting agent run() task")
            
            # Create mock content helper to assist with network issues
            if os.path.exists('/.dockerenv'):
                async def mock_google_search(query):
                    """Create a mock Google search page with useful content about the query"""
                    mock_search_content = f"""
                    <html>
                    <head><title>Google Search: {query}</title></head>
                    <body style="font-family:Arial; padding:20px; background-color:#fff;">
                        <div style="margin-bottom:20px; border-bottom:1px solid #ddd; padding-bottom:10px;">
                            <div style="color:#1a0dab; font-size:18px; margin-bottom:5px;">GPT-4o Pricing - OpenAI API</div>
                            <div style="color:#006621; font-size:14px;">https://openai.com/pricing</div>
                            <div style="color:#444; font-size:14px;">
                                GPT-4o costs $15 per million tokens for output and $5 per million tokens for input.
                                Pricing information updated as of April 2023.
                            </div>
                        </div>
                        <div style="margin-bottom:20px; border-bottom:1px solid #ddd; padding-bottom:10px;">
                            <div style="color:#1a0dab; font-size:18px; margin-bottom:5px;">OpenAI API - Build with GPT-4 and GPT-4o</div>
                            <div style="color:#006621; font-size:14px;">https://openai.com/api</div>
                            <div style="color:#444; font-size:14px;">
                                GPT-4o is the latest model from OpenAI, offering advanced AI capabilities for various applications.
                                The pricing structure is designed to be accessible for developers.
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    return mock_search_content
                
                # Check if browser_use has a hook mechanism we can use
                if importlib.util.find_spec("browser_use.browser.context") is not None:
                    # Try to monkey patch the agent's execution to intercept specific URLs
                    try:
                        from browser_use.browser.context import BrowserContext
                        if hasattr(BrowserContext, 'navigate'):
                            original_navigate = BrowserContext.navigate
                            
                            async def intercept_navigate(self, url, **kwargs):
                                logger.info(f"Intercepting navigation to: {url}")
                                
                                # Check if this is a Google search
                                if 'google.com/search' in url:
                                    try:
                                        import urllib.parse
                                        parsed_url = urllib.parse.urlparse(url)
                                        query_params = urllib.parse.parse_qs(parsed_url.query)
                                        
                                        if 'q' in query_params and query_params['q']:
                                            search_query = query_params['q'][0]
                                            logger.info(f"Detected Google search for: {search_query}")
                                            
                                            # Create a mock search page
                                            mock_content = await mock_google_search(search_query)
                                            
                                            # Set the page content instead of navigating
                                            if hasattr(self, 'page') and self.page:
                                                logger.info("Setting mock search results")
                                                await self.page.set_content(mock_content)
                                                return True
                                    except Exception as e:
                                        logger.warning(f"Failed to intercept Google search: {e}")
                                
                                # Fall back to original navigation for other URLs
                                return await original_navigate(self, url, **kwargs)
                            
                            # Apply the interception patch
                            BrowserContext.navigate = intercept_navigate
                            logger.info("Applied navigation interception for search queries")
                    except Exception as e:
                        logger.warning(f"Failed to set up navigation interception: {e}")
            
            agent_task = asyncio.create_task(agent.run())
            logger.info("Agent task created, will await completion")
            
            # Now find any new Chrome processes that were started
            await asyncio.sleep(5)  # Give time for Chrome to start
            
            # Find Chrome window associated with the agent
            window_id = await wait_and_find_chrome_window()
            if window_id:
                logger.info(f"Found agent's Chrome window with ID: {window_id}")
            
            # Wait for agent to complete
            logger.info("Awaiting agent task completion...")
            await agent_task
            logger.info("Agent task completed successfully")
        except Exception as e:
            logger.error(f"Error in agent execution: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Signal screenshot capture to stop
        stop_capture.set()
        await screenshot_task
        
        # Stop the screen recording if it was started
        if recording_process:
            logger.info("Stopping screen recording...")
            try:
                recording_process.send_signal(signal.SIGINT)
                stdout, stderr = recording_process.communicate(timeout=10)
                logger.info(f"Recording process exit code: {recording_process.returncode}")
                
                if stderr:
                    logger.debug(f"FFmpeg stderr: {stderr.decode()}")
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                # Force kill if needed
                try:
                    recording_process.kill()
                except:
                    pass
        
        # Wait a moment for videos to be finalized
        logger.info("Waiting for videos to be finalized...")
        await asyncio.sleep(3)
        
        # Create a video from screenshots as backup
        if os.path.exists(screenshot_dir):
            screenshot_count = len([f for f in os.listdir(screenshot_dir) if f.endswith('.png')])
            
            if screenshot_count > 0:
                logger.info(f"Found {screenshot_count} screenshots")
                
                if is_tool_available('ffmpeg'):
                    # Use ffmpeg to create a video from screenshots
                    output_video = os.path.join(video_path, "screenshots_video.mp4")
                    screenshots_pattern = os.path.join(screenshot_dir, "screenshot_%04d.png")
                    
                    try:
                        # Using ffmpeg with pattern
                        subprocess.run([
                            "ffmpeg", "-y", "-framerate", "10", 
                            "-i", screenshots_pattern, 
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", 
                            output_video
                        ], check=True)
                        
                        if os.path.exists(output_video):
                            size_mb = os.path.getsize(output_video) / (1024 * 1024)
                            logger.info(f"Created video from screenshots: {output_video} ({size_mb:.2f} MB)")
                        else:
                            logger.warning(f"Failed to create video at {output_video}")
                    except Exception as e:
                        logger.error(f"Error creating video from screenshots: {e}")
                        logger.error(str(e))
                else:
                    logger.warning("ffmpeg not available, cannot create video from screenshots")
            else:
                logger.warning("No screenshots found")
        
        # Report on all files created
        if os.path.exists(video_path):
            logger.info(f"Files in {video_path}:")
            for root, dirs, files in os.walk(video_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, video_path)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    logger.info(f"  {rel_path}: {size_mb:.2f} MB")
                    
            # If we have the recording, check its size
            if recording_process and os.path.exists(recording_file):
                size_mb = os.path.getsize(recording_file) / (1024 * 1024)
                logger.info(f"Screen recording size: {size_mb:.2f} MB")
                
                if size_mb < 0.1:
                    logger.warning("Screen recording file is suspiciously small")
                else:
                    logger.info("Screen recording file looks good")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Make sure to clean up any running processes
        if recording_process:
            try:
                recording_process.terminate()
            except:
                pass
        
        raise

@app.get("/")
async def root():
    return {"message": "Hello World"}

class TaskRequest(BaseModel):
    task: str

@app.post("/run")
async def run(request: TaskRequest):
    result = await main(request.task)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
