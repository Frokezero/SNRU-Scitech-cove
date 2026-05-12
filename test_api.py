import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000"

def test_api():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/me") as response:
            print(f"Status: {response.getcode()}")
            print(f"Body: {response.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Status: {e.code}")
        print(f"Body: {e.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
