import sys

def test_path():
    print("\n=== SYS.PATH ===")
    for p in sys.path:
        print(p)

    import models
    print("\nMODELS:", models)