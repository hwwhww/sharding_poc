import logging
from itertools import (
    product,
)

from eth_utils import (
    keccak,
    int_to_big_endian,
    big_endian_to_int,
)

from message import (
    create_genesis_header,
)

logger = logging.getLogger("SMC")

start_seed = keccak(b'\x00' * 32)


class SMCHandler:

    def __init__(self, num_shards, lookahead_period_length, collator_pool):
        self.num_shards = num_shards
        self.lookahead_period_length = lookahead_period_length
        self.collator_pool = collator_pool

        self.period = 1
        self.collators = {}
        self.headers_per_shard = {
            shard_id: [create_genesis_header(shard_id)] for shard_id in range(self.num_shards)
        }  # {shard_id: header chain, ...}

    def get_eligible_collator(self, period, shard_id):
        if period > self.period + self.lookahead_period_length:
            raise ValueError("Given period exceeds lookahead period")
        if shard_id not in self.headers_per_shard.keys():
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

        shards = self.headers_per_shard.keys()
        periods = range(self.period, self.period + self.lookahead_period_length + 1)
        shards_and_periods = [
            (shard_id, period)
            for shard_id, period in product(shards, periods)
            if collator == self.get_eligible_collator(period, shard_id)
        ]
        logger.info('shards_and_periods: {}'.format(shards_and_periods))
        return shards_and_periods

    def add_header(self, collator, header):
        if collator != self.get_eligible_collator(header.period, header.shard_id):
            raise ValueError("Collator is not eligible to submit header for this period and shard")
        if header.period != self.period:
            raise ValueError("Period of submitted header does not equal current period")

        current_header = self.get_head(header.shard_id)
        if header.number != current_header.number + 1:
            raise ValueError("Fork in header chain")

        self.headers_per_shard[header.shard_id].append(header)
        self.collators[header.shard_id, header.period] = collator
        logger.info('[Added Header] {}, collator: {}'.format(header, collator))
s

    def get_head(self, shard_id):
        logger.info('in get_header, self.headers_per_shard: {}'.format(
            self.headers_per_shard)
        )
        return self.headers_per_shard[shard_id][-1]
