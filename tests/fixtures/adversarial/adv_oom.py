
arr = []
try:
    while True:
        arr.append("A" * 1024 * 1024 * 10) # 10MB chunks
except MemoryError:
    print("FAILED: MemoryError caught")
print("ALIVE")
