"""Fixture with deliberately risky patterns, used to test ScriptOS's static risk scan."""
import os
import pickle

print(eval("1+1"))
os.system("echo hi")
pickle.loads(b"")
