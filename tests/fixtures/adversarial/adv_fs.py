
try:
    with open("/etc/shadow", "r") as f:
        print("SUCCESS")
except Exception as e:
    print(f"FAILED: {str(e)}")
