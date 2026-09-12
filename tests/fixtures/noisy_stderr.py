import sys

for i in range(20000):
    print(f"warning line {i}", file=sys.stderr)
print("done")
