from playwright.sync_api import sync_playwright
import time

def interact_with_chat():
    with sync_playwright() as p:
        # Launch browser in non-headless mode
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Navigating to http://localhost:3001...")
        page.goto('http://localhost:3001')

        # Wait for the page to fully load
        page.wait_for_load_state('networkidle')
        print("Page loaded")

        # Wait a bit for any JavaScript to initialize
        page.wait_for_timeout(2000)

        # Try to find and enable the input field
        print("\nLooking for input field...")

        # Try different selectors for the input
        selectors = [
            'input[placeholder*="Ask"]',
            'input[type="text"]',
            'textarea',
            '.chat-input',
            'input'
        ]

        input_field = None
        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    print(f"Found element with selector: {selector}")
                    input_field = element
                    break
            except:
                continue

        if input_field:
            # Check if the input is disabled
            is_disabled = input_field.is_disabled()
            print(f"Input field disabled: {is_disabled}")

            # Check if input is editable
            is_editable = input_field.is_editable()
            print(f"Input field editable: {is_editable}")

            # Try to focus on the input
            print("\nTrying to focus on input field...")
            input_field.focus()
            page.wait_for_timeout(500)

            # Try clicking on it
            print("Clicking on input field...")
            try:
                input_field.click()
                page.wait_for_timeout(500)
            except Exception as e:
                print(f"Could not click: {e}")

            # Try to type directly
            print("\nTrying to type in the field...")
            try:
                # Force focus and type
                page.evaluate(f'''
                    const input = document.querySelector('{selectors[0]}') || document.querySelector('input[type="text"]');
                    if (input) {{
                        input.removeAttribute('disabled');
                        input.focus();
                        input.value = 'What is the LM317 voltage regulator?';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                ''')
                print("Text inserted via JavaScript")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"JavaScript insertion failed: {e}")

            # Try pressing Enter to submit
            print("\nTrying to submit with Enter key...")
            try:
                page.keyboard.press('Enter')
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Enter key failed: {e}")

            # Look for a send button and click it
            print("\nLooking for send button...")
            send_selectors = [
                'button[aria-label*="send"]',
                'button svg',  # Button with icon
                'button',
                '[role="button"]'
            ]

            for selector in send_selectors:
                try:
                    button = page.query_selector(selector)
                    if button:
                        print(f"Found button with selector: {selector}")
                        button.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    continue

        # Alternative: Try clicking on one of the example queries
        print("\n\nTrying to click on an example query...")
        example_queries = page.query_selector_all('.flex.items-center.gap-2')
        if example_queries:
            print(f"Found {len(example_queries)} example query buttons")
            if len(example_queries) > 0:
                print("Clicking on first example query...")
                try:
                    example_queries[0].click()
                    page.wait_for_timeout(3000)
                    print("Clicked example query")
                except Exception as e:
                    print(f"Could not click example: {e}")

        # Take a screenshot of the final state
        page.screenshot(path='playwright_final_state.png')
        print("\nScreenshot saved as 'playwright_final_state.png'")

        # Get current page state
        print("\n=== Current Page State ===")
        page_text = page.inner_text('body')
        print(page_text[:500] if len(page_text) > 500 else page_text)

        print("\n=== Browser is open for manual interaction ===")
        print("You can now interact with the page manually.")
        print("Press Enter in this terminal when done...")
        input()

        browser.close()

if __name__ == "__main__":
    interact_with_chat()