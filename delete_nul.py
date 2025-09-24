import os
import subprocess

# Try to delete the nul file using Windows special path syntax
path = r'\\?\C:\Users\vinee\Documents\htdocs\z2data\agents-hosted-simple\nul'

try:
    # Method 1: Using os.remove with special path
    os.remove(path)
    print("Successfully deleted nul file using os.remove")
except Exception as e:
    print(f"os.remove failed: {e}")

    try:
        # Method 2: Using subprocess with cmd
        result = subprocess.run(['cmd', '/c', f'del "{path}"'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Successfully deleted nul file using cmd")
        else:
            print(f"cmd del failed: {result.stderr}")
    except Exception as e2:
        print(f"subprocess failed: {e2}")