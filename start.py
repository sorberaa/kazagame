"""Резервная точка входа для платформ вроде Render, если в Start Command указано `python start.py`."""
import asyncio
from bot import main

if __name__ == "__main__":
    asyncio.run(main())

