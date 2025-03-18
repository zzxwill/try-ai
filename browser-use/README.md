# Browser Automation with Playwright

This project uses Playwright for browser automation and testing.

## Installation

To install Playwright, run:

```bash
# Install Playwright
npm init playwright@latest
```

During the installation process, you'll be prompted to make several choices:

1. Choose between TypeScript or JavaScript (we selected TypeScript)
2. Specify where to put your end-to-end tests (we selected the default 'tests' directory)
3. Choose whether to add a GitHub Actions workflow (we selected 'No')
4. Choose whether to install Playwright browsers automatically (we selected 'Yes')

The installation process will:

- Initialize an NPM project (if not already initialized)
- Install Playwright Test (`@playwright/test`)
- Install TypeScript types (`@types/node`)
- Create configuration files (`playwright.config.ts`)
- Create example test files
- Download browsers (Chromium, Firefox, and WebKit)

## Available Commands

After installation, you can use the following commands:

```bash
# Run all tests
npx playwright test

# Start the interactive UI mode
npx playwright test --ui

# Run tests only on Chrome
npx playwright test --project=chromium

# Run tests in a specific file
npx playwright test example

# Run tests in debug mode
npx playwright test --debug

# Auto-generate tests with Codegen
npx playwright codegen
```

## Project Structure

The installation creates the following key files:

- `./tests/example.spec.ts` - Example end-to-end test
- `./tests-examples/demo-todo-app.spec.ts` - Demo Todo App end-to-end tests
- `./playwright.config.ts` - Playwright Test configuration

## Usage

After installation, you can use Playwright for browser automation and testing.

For more information, visit the [Playwright documentation](https://playwright.dev/docs/intro).

## Running with Visible Browser

By default, Playwright runs browsers in headless mode (without a visible UI). If you want to see the browser in action, you can use the following commands:

```bash
# Run a simple visible browser demo
make run-demo

# Run a quick visible browser test
make run-visible
```

The `visible_browser.py` script demonstrates browser automation with a visible browser window. It navigates to websites, performs searches, and takes screenshots.

## Browser Video Recording

Playwright provides a powerful video recording feature that allows you to capture browser interactions even when running in headless mode or in environments like Kubernetes where you can't see the browser directly.

### Running Video Recording Locally

```bash
# Run the video recording demo
make run-record
```

This will:

1. Run the browser in headless mode
2. Record all browser interactions as a video
3. Save the video to the `videos/` directory

### Docker

Build and run the Docker container:

```bash
# Build the Docker image
make docker-build

# Run the container locally
➜  browser-use git:(master) ✗ make docker-run
Running Docker container...
docker run -it --rm -e OPENAI_API_KEY="$OPENAI_API_KEY" browser-use:latest
The XKEYBOARD keymap compiler (xkbcomp) reports:
> Warning:          Could not resolve keysym XF86CameraAccessEnable
> Warning:          Could not resolve keysym XF86CameraAccessDisable
> Warning:          Could not resolve keysym XF86CameraAccessToggle
> Warning:          Could not resolve keysym XF86NextElement
> Warning:          Could not resolve keysym XF86PreviousElement
> Warning:          Could not resolve keysym XF86AutopilotEngageToggle
> Warning:          Could not resolve keysym XF86MarkWaypoint
> Warning:          Could not resolve keysym XF86Sos
> Warning:          Could not resolve keysym XF86NavChart
> Warning:          Could not resolve keysym XF86FishingChart
> Warning:          Could not resolve keysym XF86SingleRangeRadar
> Warning:          Could not resolve keysym XF86DualRangeRadar
> Warning:          Could not resolve keysym XF86RadarOverlay
> Warning:          Could not resolve keysym XF86TraditionalSonar
> Warning:          Could not resolve keysym XF86ClearvuSonar
> Warning:          Could not resolve keysym XF86SidevuSonar
> Warning:          Could not resolve keysym XF86NavInfo
Errors from xkbcomp are not fatal to the X server
INFO     [browser_use] BrowserUse logging setup complete with level info
INFO     [root] Anonymized telemetry enabled. See https://docs.browser-use.com/development/telemetry for more information.
INFO     [__main__] Starting price comparison task...
/usr/local/lib/python3.12/dist-packages/browser_use/agent/message_manager/views.py:59: LangChainBetaWarning: The function `load` is in beta. It is actively being worked on, so the API may change.
  value['message'] = load(value['message'])
INFO     [__main__] Agent created successfully
INFO     [agent] 🚀 Starting task: Check the price of gpt-4o
INFO     [agent] 📍 Step 1
INFO     [agent] 🤷 Eval: Unknown - Starting new task to determine the price of gpt-4o.
INFO     [agent] 🧠 Memory: Task started: Check the price of gpt-4o. Opened the browser, currently at 0/1 price checks.
INFO     [agent] 🎯 Next goal: Search for gpt-4o price in Google.
INFO     [agent] 🛠️  Action 1/1: {"search_google":{"query":"gpt-4o pricing"}}
INFO     [controller] 🔍  Searched for "gpt-4o pricing" in Google
INFO     [agent] 📍 Step 2
INFO     [agent] 👍 Eval: Success - Found multiple sources listing prices for GPT-4o.
INFO     [agent] 🧠 Memory: Found price information for GPT-4o: $15 per million tokens for output and $5 per million tokens for input according to a search result. Task completed 1/1 price checks.
INFO     [agent] 🎯 Next goal: Finish the task as the price information is obtained.
INFO     [agent] 🛠️  Action 1/1: {"done":{"text":"The price of GPT-4o is $15 per million tokens for output and $5 per million tokens for input.","success":true}}
INFO     [agent] 📄 Result: The price of GPT-4o is $15 per million tokens for output and $5 per million tokens for input.
INFO     [agent] ✅ Task completed
INFO     [agent] ✅ Successfully
The XKEYBOARD keymap compiler (xkbcomp) reports:
> Warning:          Could not resolve keysym XF86CameraAccessEnable
> Warning:          Could not resolve keysym XF86CameraAccessDisable
> Warning:          Could not resolve keysym XF86CameraAccessToggle
> Warning:          Could not resolve keysym XF86NextElement
> Warning:          Could not resolve keysym XF86PreviousElement
> Warning:          Could not resolve keysym XF86AutopilotEngageToggle
> Warning:          Could not resolve keysym XF86MarkWaypoint
> Warning:          Could not resolve keysym XF86Sos
> Warning:          Could not resolve keysym XF86NavChart
> Warning:          Could not resolve keysym XF86FishingChart
> Warning:          Could not resolve keysym XF86SingleRangeRadar
> Warning:          Could not resolve keysym XF86DualRangeRadar
> Warning:          Could not resolve keysym XF86RadarOverlay
> Warning:          Could not resolve keysym XF86TraditionalSonar
> Warning:          Could not resolve keysym XF86ClearvuSonar
> Warning:          Could not resolve keysym XF86SidevuSonar
> Warning:          Could not resolve keysym XF86NavInfo
Errors from xkbcomp are not fatal to the X server
INFO     [__main__] Price check completed successfully
```
