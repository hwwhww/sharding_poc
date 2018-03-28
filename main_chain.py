import asyncio
import logging


logger = logging.getLogger("main_chain")


BLOCK_TIME = 1
PERIOD_LENGTH = 5
PERIOD_TIME = PERIOD_LENGTH * BLOCK_TIME


async def wait_for_next_block():
    await asyncio.sleep(BLOCK_TIME)  # TODO: poissonian distribution


class MainChain:

    def __init__(self):
        self.block = 0

    async def run(self):
        while True:
            await wait_for_next_block()
            self.block += 1
            logger.info('new block: {}'.format(self.block))
