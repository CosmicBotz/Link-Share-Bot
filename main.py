"""
main.py
~~~~~~~
Entry point.  Simply instantiates the Bot and runs it.
"""
import asyncio

from bot import Bot


async def main():
    bot = Bot()
    await bot.start()
    # Keep running until interrupted
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
