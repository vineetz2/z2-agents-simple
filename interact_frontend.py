from playwright.sync_api import sync_playwright
import time

def interact_with_frontend():
    with sync_playwright() as p:
        # Launch browser in non-headless mode so you can see it
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Navigating to http://localhost:3001...")
        page.goto('http://localhost:3001')

        # Wait for page to load
        page.wait_for_load_state('networkidle')

        print("\nPage loaded. Taking screenshot...")
        page.screenshot(path='frontend_initial.png')

        # Check for input fields
        print("\nLooking for input fields...")
        inputs = page.query_selector_all('input, textarea')
        print(f"Found {len(inputs)} input fields")

        # Try to find the main chat/message input
        chat_input = page.query_selector('input[type="text"], textarea')
        if chat_input:
            print("\nFound text input field")
            print("Clicking on input field...")
            chat_input.click()
            time.sleep(1)

            print("Typing test message...")
            chat_input.type("Hello, this is a test message", delay=100)
            time.sleep(2)

            # Look for send button
            send_button = page.query_selector('button')
            if send_button:
                print("Found send button, clicking...")
                send_button.click()
                time.sleep(2)

        # Check page state after interaction
        print("\nChecking page elements...")
        all_buttons = page.query_selector_all('button')
        print(f"Found {len(all_buttons)} buttons")

        # Get all visible text
        page_text = page.inner_text('body')
        print("\nVisible text on page:")
        print(page_text[:500] if len(page_text) > 500 else page_text)

        # Take final screenshot
        page.screenshot(path='frontend_after_interaction.png')
        print("\nScreenshot saved as 'frontend_after_interaction.png'")

        # Keep browser open for manual interaction
        print("\n=== Browser is now open for manual interaction ===")
        print("You can interact with the page manually.")
        print("Press Enter in this terminal when done to close the browser...")
        input()

        browser.close()

if __name__ == "__main__":
    interact_with_frontend()