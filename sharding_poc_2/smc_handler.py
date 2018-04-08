import asyncio

import logging
from collections import (
    defaultdict,
)
from itertools import (
    chain,
    product,
)
import time

from eth_utils import (
    keccak,
    int_to_big_endian,
    big_endian_to_int,
)

from message import (
    create_genesis_header,
)

from main_chain import (
    BLOCK_TIME,
    PERIOD_LENGTH,
)

logger = logging.getLogger("SMC")

start_seed = keccak(b'\x00' * 32)

POLLING_CYCLE = BLOCK_TIME / 5


class Shard:

    def __init__(self, smc_handler, shard_id):
        self.smc_handler = smc_handler
        self.shard_id = shard_id

        self.headers_by_hash = {}
        self.headers_by_number = defaultdict(list)  # header lists sorted by period (oldest first)
        self.best_number = 0

        # insert genesis
        genesis_header = create_genesis_header(shard_id)
        self.headers_by_hash[genesis_header.hash] = genesis_header
        self.headers_by_number[genesis_header.number] += [genesis_header]
        self.best_number = genesis_header.number

    def add_header(self, header):
        if header.hash in self.headers_by_hash:
            raise ValueError("Header already added")
        if header.shard_id != self.shard_id:
            raise ValueError("Header belongs to different shard")
        max_period = max(h.period for h in self.headers_by_hash.values())
        if header.period <= max_period:
            raise ValueError("Header period not increasing")

        self.headers_by_hash[header.hash] = header
        self.headers_by_number[header.number] += [header]

        self.best_number = max(self.best_number, header.number)

    def get_candidate_head_iterator(self):
        for number in reversed(range(-1, self.best_number + 1)):
            for header in self.headers_by_number[number]:
                yield header

    def get_head(self, availabilities=None):
        head = self.get_candidate_head(availabilities)
        if head is None:
            raise ValueError("No available head")


class SMCHandler:

    def __init__(self, main_chain, num_shards, lookahead_period_length, collator_pool):
        self.main_chain = main_chain

        self.num_shards = num_shards
        self.lookahead_period_length = lookahead_period_length
        self.collator_pool = collator_pool

        self.collators = {}
        self.shard_ids = list(range(self.num_shards))
        self.shards = {shard_id: Shard(self, shard_id) for shard_id in self.shard_ids}

        self.new_period_event = asyncio.Event()  # triggered whenever a new period starts
        self.new_block_event = asyncio.Event()  # triggered whenever a new block appears

        self._time_at_last_check = 0.0
        self._block_at_last_check = self.main_chain.block - 1
        self._period_at_last_check = None
        self.check_main_chain()

    def check_main_chain(self):
        self._time_at_last_check = time.time()
        if self.main_chain.block != self._block_at_last_check:
            assert self.main_chain.block > self._block_at_last_check

            if self._block_at_last_check > self.main_chain.block + 1:
                logger.warning("Missed main chain blocks after height {}".format(
                    self._block_at_last_check,
                ))

            self._block_at_last_check += 1
            period_at_last_check = self._period_at_last_check
            self._period_at_last_check = self.main_chain.block // PERIOD_LENGTH

            self.new_block_event.set()
            self.new_block_event.clear()
            if self._period_at_last_check != period_at_last_check:
                logger.info("period {} start".format(self._period_at_last_check))
                self.new_period_event.set()
                self.new_period_event.clear()

    async def run(self):
        while True:
            # make sure main chain is checked at least every POLLING_CYCLE
            if time.time() - self._time_at_last_check >= POLLING_CYCLE:
                self.check_main_chain()

            # sleep until POLLING_CYCLE seconds have passed since last check
            await asyncio.sleep(POLLING_CYCLE - (time.time() - self._time_at_last_check))

    async def wait_for_period(self, period):
        if period < self.get_current_period():
            raise ValueError("Period already passed")

        while self.get_current_period() < period:
            await self.new_period_event.wait()

    async def wait_for_next_period(self):
        current_period = self.get_current_period()
        await self.wait_for_period(current_period + 1)

    async def wait_for_block(self, block):
        if block < self.get_current_block():
            raise ValueError("Block already passed")

        while self.get_current_block() < block:
            await self.new_block_event.wait()

    async def wait_for_next_block(self):
        current_block = self.get_current_block()
        await self.wait_for_block(current_block + 1)

    def get_current_period(self):
        self.check_main_chain()
        return self.main_chain.block // PERIOD_LENGTH

    def get_current_block(self):
        self.check_main_chain()
        return self.main_chain.block

    def get_eligible_collator(self, period, shard_id):
        if period > self.get_current_period() + self.lookahead_period_length:
            raise ValueError("Given period exceeds lookahead period")
        if shard_id not in self.shard_ids:
            raise ValueError("No shard with ID {}".format(shard_id))

        seed = start_seed
        for i in range(period):
            seed = keccak(seed + int_to_big_endian(i))

        collator_number = (
            big_endian_to_int(keccak(seed + int_to_big_endian(shard_id))) % len(self.collator_pool)
        )
        return self.collator_pool[collator_number]

    def get_eligible_periods(self, collator):
        if collator not in self.collator_pool:
            raise ValueError("Collator {} not in collator pool".format(collator))

        current_period = self.get_current_period()
        periods = range(current_period, current_period + self.lookahead_period_length + 1)
        shards_and_periods = [
            (shard_id, period)
            for shard_id, period in product(self.shard_ids, periods)
            if collator == self.get_eligible_collator(period, shard_id)
        ]
        return shards_and_periods

    def add_header(self, collator, header):
        if collator != self.get_eligible_collator(header.period, header.shard_id):
            raise ValueError("Collator is not eligible to submit header for this period and shard")
        if header.period != self.get_current_period():
            raise ValueError("Period of submitted header does not equal current period")

        self.shards[header.shard_id].add_header(header)
        self.collators[header.shard_id, header.period] = collator
        logger.info('[Added Header] {}, collator: {}'.format(header, collator))
