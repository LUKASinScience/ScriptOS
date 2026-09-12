import time

blocks = []
for _ in range(200):
    blocks.append(bytearray(10 * 1024 * 1024))  # 10 MB per block
    time.sleep(0.05)
print("finished without being stopped")
