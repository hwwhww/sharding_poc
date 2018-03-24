import asyncio


BLOCK_TIME = 2
PERIOD_LENGTH = 5
PERIOD_TIME = PERIOD_LENGTH * BLOCK_TIME


async def main_chain(smc):
    while True:
        await asyncio.sleep(PERIOD_TIME)
        smc.period += 1
