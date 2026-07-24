import json
import numpy as np

def test_numpy():
    try:
        obj = {"val": np.int64(0)}
        json.dumps(obj)
        print("Success")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_numpy()
