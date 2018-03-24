from eth_utils import (
    keccak,
    int_to_big_endian,
    big_endian_to_int,
)

from message import (
    create_genesis_header,
)


# loog_ahead_period_length = 5
# windback_period_length = 25
# collation_pool = [keccak(int_to_big_endian(i)) for i in range(20)]
start_seed = keccak(b'\x00' * 32)


# def get_look_ahead_period_length():
#     return loog_ahead_period_length


# def get_windback_period_length():
#     return windback_period_length


# def get_eligible_collator(period, shard_id):
#     seed = start_seed
#     for i in range(period):
#         seed = keccak(seed + int_to_big_endian(i))

#     collator_number = big_endian_to_int(keccak(seed + int_to_big_endian(shard_id))) % len(collation_pool)
#     return (
#         collator_number,
#         collation_pool[collator_number],
#     )


# def get_collation_head(period, shard_id):
#     _, collator_addr = get_eligible_collator(period, shard_id)
#     _, prev_collation_addr = get_eligible_collator(period-1, shard_id)

#     header = {
#         "period": period,
#         "shard_id": shard_id,
#         "collator": collator_addr,
#         "header_hash": keccak(collator_addr + int_to_big_endian(period) + int_to_big_endian(shard_id)),
#         "parent_header_hash": keccak(prev_collation_addr + int_to_big_endian(period-1) + int_to_big_endian(shard_id)),
#     }
#     return header


# def add_header(period, shard_id, collator_addr):
#     _, eligible_collator_addr = get_eligible_collator(period, shard_id)
#     assert collator_addr == eligible_collator_addr


class SMCHandler:

    def __init__(self, num_shards, lookahead_period_length, collator_pool):
        self.num_shards = num_shards
        self.lookahead_period_length = lookahead_period_length
        self.collator_pool = collator_pool

        self.period = 1
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

    def get_eligible_periods(self, shard_id, collator):
        if shard_id not in self.headers_per_shard.keys():
            raise ValueError("No shard with ID {}".format(shard_id))
        if collator not in self.collator_pool:
            raise ValueError("Collator {} not in collator pool".format(collator))

        periods = [
            period
            for period in range(self.period, self.period + self.lookahead_period_length + 1)
            if collator == self.get_eligible_collator(period, shard_id)
        ]
        return periods

    def add_header(self, collator, header):
        if collator != self.get_eligible_collator(header.period, header.shard_id):
            raise ValueError("Collator is not eligible to submit header for this period and shard")
        if header.period != self.period:
            raise ValueError("Period of submitted header does not equal current period")

        current_header = self.get_head(header.shard_id)
        if header.number != current_header.number + 1:
            raise ValueError("Fork in header chain")

        self.headers_per_shard[header.shard_id].append(current_header)

    def get_head(self, shard_id):
        return self.headers_per_shard[shard_id][-1]
