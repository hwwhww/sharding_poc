import asyncio
import logging


logger = logging.getLogger("main_chain")


BLOCK_TIME = 1
PERIOD_LENGTH = 5
PERIOD_TIME = PERIOD_LENGTH * BLOCK_TIME


async def main_chain(smc):
    while True:
        await asyncio.sleep(PERIOD_TIME)
        smc.period += 1
        logger.info('period added')
