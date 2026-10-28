from .cli import main

if __name__ == "__main__":  # guard needed: analysis worker processes re-import this module
    raise SystemExit(main())
