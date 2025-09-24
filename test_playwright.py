from playwright.sync_api import sync_playwright
import time

def test_chat_interface():
    with sync_playwright() as p:
        # Launch browser in visible mode
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Opening http://localhost:3001...")
        page.goto('http://localhost:3001')

        # Wait for page to fully load and WebSocket to connect
        print("Waiting for page to load and WebSocket to connect...")
        page.wait_for_timeout(3000)  # Give time for WebSocket connection

        # Take screenshot to see current state
        page.screenshot(path='chat_interface_loaded.png')
        print("Screenshot saved as 'chat_interface_loaded.png'")

        # Check if the input is now enabled
        input_selector = 'input[placeholder="Ask something..."]'
        input_field = page.query_selector(input_selector)

        if input_field:
            is_disabled = input_field.is_disabled()
            print(f"\nInput field found. Disabled: {is_disabled}")

            if not is_disabled:
                # Click on the input field
                print("Clicking on input field...")
                input_field.click()

                # Type a test message
                test_message = "What is the LM317 voltage regulator?"
                print(f"Typing: {test_message}")
                input_field.type(test_message, delay=50)

                # Take screenshot with typed text
                page.screenshot(path='chat_with_text.png')
                print("Screenshot with text saved")

                # Find and click send button
                send_button = page.query_selector('.landing-send-button')
                if send_button:
                    print("Clicking send button...")
                    send_button.click()
                else:
                    # Try pressing Enter
                    print("Pressing Enter to send...")
                    page.keyboard.press('Enter')

                # Wait for response
                print("Waiting for response...")
                page.wait_for_timeout(5000)

                # Take final screenshot
                page.screenshot(path='chat_with_response.png')
                print("Final screenshot saved as 'chat_with_response.png'")

            else:
                print("\nInput is still disabled. Trying to click an example button instead...")
                # Try clicking an example button
                example_buttons = page.query_selector_all('.landing-example-button')
                if example_buttons and len(example_buttons) > 0:
                    print(f"Found {len(example_buttons)} example buttons")
                    print("Clicking first example button...")
                    example_buttons[0].click()

                    # Wait for response
                    page.wait_for_timeout(5000)

                    # Take screenshot
                    page.screenshot(path='chat_example_response.png')
                    print("Screenshot saved as 'chat_example_response.png'")

        # Check the console for errors
        page.on('console', lambda msg: print(f'Console: {msg.text}'))

        print("\n=== Browser is open for manual testing ===")
        print("You can interact with the page manually now.")
        print("Press Enter to close the browser...")
        input()

        browser.close()

if __name__ == "__main__":
    test_chat_interface()