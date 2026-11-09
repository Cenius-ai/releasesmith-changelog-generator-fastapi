"""``python -m app`` seeds the database, mirroring ``python -m app.seed``."""

from app.seed import main

if __name__ == "__main__":
    main()
