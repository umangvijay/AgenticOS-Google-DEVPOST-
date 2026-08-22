
import urllib.request
try:
    urllib.request.urlopen("http://example.com", timeout=2)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {str(e)}")
