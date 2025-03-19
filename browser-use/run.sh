#!/bin/bash

# Exit on any error
set -e

# Create test screenshot directory
mkdir -p /tmp/test-screenshots

# Create proper fluxbox configuration
mkdir -p /root/.fluxbox
cat > /root/.fluxbox/init << 'EOF'
session.screen0.toolbar.visible: false
session.screen0.toolbar.autoHide: true
session.screen0.titlebar.left: Stick
session.screen0.titlebar.right: Minimize Maximize Close
session.screen0.window.focus.alpha: 255
session.screen0.window.unfocus.alpha: 255
session.screen0.menu.alpha: 255
session.screen0.clientMenu.usePixmap: true
EOF

# Create browser_use_patch.py
echo "Creating browser_use_patch.py in /tmp"
cat > /tmp/browser_use_patch.py << 'EOF'
import os, sys, subprocess, logging, inspect
logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger('browser_use_patch')

# Monkey patch subprocess.check_output to handle xdotool failures
original_check_output = subprocess.check_output
def patched_check_output(cmd, *args, **kwargs):
    try:
        return original_check_output(cmd, *args, **kwargs)
    except subprocess.CalledProcessError as e:
        if isinstance(cmd, str) and ('xdotool search' in cmd):
            logger.warning('xdotool command failed, returning empty result: ' + str(cmd))
            return b''
        raise e
subprocess.check_output = patched_check_output

# Add patch for Playwright browser launch
try:
    from playwright.async_api import ChromiumBrowser
    from playwright.async_api import Error as PlaywrightError
    
    # Store the original launch method
    original_launch = ChromiumBrowser.launch
    
    # Create patched version with better error handling
    async def patched_launch(self, **kwargs):
        try:
            logger.info("Attempting to launch browser with patched method")
            return await original_launch(self, **kwargs)
        except PlaywrightError as e:
            logger.warning(f"Browser launch failed: {e}")
            # Try again with a brief delay
            import asyncio
            await asyncio.sleep(1)
            logger.info("Retrying browser launch...")
            return await original_launch(self, **kwargs)
    
    # Apply the patch
    ChromiumBrowser.launch = patched_launch
    logger.info("Applied patch to Chromium browser launch method for better error handling")
except (ImportError, AttributeError) as e:
    logger.info(f"Failed to patch Playwright browser: {e}")
    logger.info("Skipping Playwright-specific patches")

logger.info('Browser-use patching completed: xdotool failures will be handled gracefully')

# Basic browser_use patching will be done at runtime
EOF

# Start Xvfb with optimized parameters for rendering
echo "Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to initialize fully
echo "Waiting for Xvfb to initialize..."
sleep 5

# Start dbus in system mode
echo "Starting dbus..."
mkdir -p /var/run/dbus
dbus-daemon --system --fork

# Start fluxbox window manager
echo "Starting window manager..."
which fluxbox || (apt-get update && apt-get install -y fluxbox)
DISPLAY=:99 fluxbox &
FLUXBOX_PID=$!
sleep 3

# Fix the wallpaper issue
echo "Setting Fluxbox wallpaper..."

# Create a simple image for wallpaper
cat > /tmp/solid_color.xpm << 'EOF'
/* XPM */
static char * solid_color_xpm[] = {
"4 4 1 1",
"  c #3498db",
"    ",
"    ",
"    ",
"    "};
EOF

# Disable fbsetbg's automatic wallpaper setting
mkdir -p /root/.fluxbox
touch /root/.fluxbox/lastwallpaper

# Create a custom fbsetbg script to override the system one
cat > /tmp/fbsetbg << 'EOF'
#!/bin/sh
# This is a dummy fbsetbg that does nothing but succeed
echo "Dummy fbsetbg called with: $@"
exit 0
EOF
chmod +x /tmp/fbsetbg
export PATH="/tmp:$PATH"

# Set DISPLAY variable explicitly
export DISPLAY=:99

# Try multiple methods in order of reliability
echo "Setting solid color background using multiple methods..."

# Try direct X11 method first
which xsetroot && xsetroot -solid "#3498db" 

# Use feh if available (more reliable than display)
which feh || apt-get install -y feh
feh --bg-tile /tmp/solid_color.xpm || feh --bg-scale /tmp/solid_color.xpm || feh --bg-color "#3498db"

# Make sure we've installed the necessary tool
which xsetroot || apt-get install -y x11-xserver-utils
xsetroot -solid "#3498db"

# Reset the fluxbox session to apply changes
which fluxbox-remote && fluxbox-remote restart

# Give the window manager a moment to process the background changes
sleep 2

# Set xhost permissions to allow connections
echo "Setting X permissions..."
xhost +local:

# Verify X server is working correctly
echo "Testing X server connection..."
xdpyinfo | grep "depth of root" || (echo "ERROR: X server not available or not configured properly"; exit 1)

# Create a simple test HTML file if it doesn't exist
if [ ! -f "/tmp/test.html" ]; then
    echo "Creating test HTML file"
    cat > /tmp/test.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Test Content</title>
    <style>
        body { 
            background-color: #3498db; 
            color: white; 
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        h1 { font-size: 48px; }
    </style>
</head>
<body>
    <h1>Test Content - This is not a black screen!</h1>
</body>
</html>
EOF
fi

# Make sure /tmp is in Python's path
export PYTHONPATH="/tmp:$PYTHONPATH"

# Test browser rendering with a simple HTML page
echo "Testing browser rendering capabilities..."
python3 -c "
import os
import sys
sys.path.insert(0, '/tmp')

# Import the patch before importing playwright
try:
    import browser_use_patch
    print('Successfully imported browser_use_patch')
except ImportError as e:
    print('Failed to import browser_use_patch:', e)

import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    try:
        print('Testing display with Playwright browser (async API)...')
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-gpu', 
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-accelerated-jpeg-decoding',
                    '--disable-accelerated-mjpeg-decode',
                    '--disable-accelerated-video-decode'
                ]
            )
            
            print('Browser launched:', await browser.version())
            
            page = await browser.new_page(viewport={'width': 1280, 'height': 720})
            await page.goto('file:///tmp/test.html')
            print('Test page loaded')
            
            test_screenshot = '/tmp/test-screenshots/browser-test.png'
            await page.screenshot(path=test_screenshot)
            
            if os.path.exists(test_screenshot):
                print(f'Screenshot captured successfully: {os.path.getsize(test_screenshot)} bytes')
                try:
                    from PIL import Image
                    img = Image.open(test_screenshot)
                    extrema = img.convert('L').getextrema()
                    if extrema[0] < 5 and extrema[1] < 5:
                        print('WARNING: Test screenshot appears to be all black!')
                    else:
                        print('Screenshot has visible content - browser rendering is working!')
                except ImportError:
                    print('PIL not available to analyze screenshot')
            
            await browser.close()
    except Exception as e:
        print(f'Browser testing error: {type(e).__name__}: {e}')

if __name__ == '__main__':
    asyncio.run(test_browser())
"

# Apply browser patching
echo "Applying browser-use patches..."
# Make sure /tmp is in Python's path
export PYTHONPATH="/tmp:$PYTHONPATH"

# Verify the browser_use_patch.py file exists
if [ -f "/tmp/browser_use_patch.py" ]; then
    echo "browser_use_patch.py found at /tmp/browser_use_patch.py"
    ls -la /tmp/browser_use_patch.py
else
    echo "ERROR: browser_use_patch.py not found in /tmp"
    exit 1
fi

# Run the application with patched browser_use
echo "Starting application..."
python3 -c '
import sys
sys.path.insert(0, "/tmp")
print("Python path:", sys.path)

# Import the basic patch first
try:
    import browser_use_patch
    print("Successfully imported browser_use_patch")
except ImportError as e:
    print("Failed to import browser_use_patch:", e)
    exit(1)

# Now apply the dynamic patching
try:
    import importlib.util
    import inspect
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    logger = logging.getLogger("runtime_patch")

    if importlib.util.find_spec("browser_use") is not None:
        import browser_use.browser.context
        
        # Store names used for patching
        browser_method_candidates = [
            "launch_browser", "_launch_browser", "create_browser", "_create_browser",
            "get_browser", "_get_browser", "setup_browser", "_setup_browser"
        ]
        
        page_method_candidates = [
            "new_page", "_new_page", "create_page", "_create_page", 
            "get_page", "_get_page", "setup_page", "_setup_page"
        ]
        
        # Log what methods are available
        context_class = browser_use.browser.context.BrowserContext
        available_methods = [m for m in dir(context_class) if not m.startswith("__")]
        logger.info("Available BrowserContext methods: " + str(available_methods))
        
        # Store original methods
        original_methods = {}
        
        # Patch browser methods
        for method_name in browser_method_candidates:
            if hasattr(context_class, method_name):
                original_method = getattr(context_class, method_name)
                
                if inspect.iscoroutinefunction(original_method):
                    original_methods[method_name] = original_method
                    
                    # Define the replacement method - using a wrapper function to avoid closure issues
                    def create_browser_wrapper(method_name):
                        async def wrapper(self, *args, **kwargs):
                            try:
                                return await original_methods[method_name](self, *args, **kwargs)
                            except Exception as e:
                                logger.warning(method_name + " failed: " + str(type(e).__name__) + ": " + str(e))
                                from playwright.async_api import async_playwright
                                p = await async_playwright()
                                browser = await p.chromium.launch(
                                    headless=True,
                                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
                                )
                                return browser
                        return wrapper
                    
                    # Apply patch
                    setattr(context_class, method_name, create_browser_wrapper(method_name))
                    logger.info("Patched browser method: " + method_name)
        
        # Patch page methods
        for method_name in page_method_candidates:
            if hasattr(context_class, method_name):
                original_method = getattr(context_class, method_name)
                
                if inspect.iscoroutinefunction(original_method):
                    original_methods[method_name] = original_method
                    
                    # Define the replacement method - using a wrapper function to avoid closure issues
                    def create_page_wrapper(method_name):
                        async def wrapper(self, *args, **kwargs):
                            try:
                                return await original_methods[method_name](self, *args, **kwargs)
                            except Exception as e:
                                logger.warning(method_name + " failed: " + str(type(e).__name__) + ": " + str(e))
                                if hasattr(self, "browser") and self.browser:
                                    return await self.browser.new_page()
                                raise
                        return wrapper
                    
                    # Apply patch
                    setattr(context_class, method_name, create_page_wrapper(method_name))
                    logger.info("Patched page method: " + method_name)
        
        logger.info("Applied patches to browser_use methods")
except Exception as e:
    logger.warning("Failed to apply browser_use patches: " + str(e))

logging.info("Starting main.py with browser-use patches applied")
import runpy
runpy.run_module("main", run_name="__main__")
' "$@"

# Cleanup
echo "Shutting down..."
if [ ! -z "$FLUXBOX_PID" ]; then
    kill $FLUXBOX_PID || true
fi
if [ ! -z "$XVFB_PID" ]; then
    kill $XVFB_PID || true
fi
pkill -f dbus-daemon || true
