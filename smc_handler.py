from eth_utils import (
    keccak,
    int_to_big_endian,
    big_endian_to_int,
)


loog_ahead_period_length = 5
windback_period_length = 25
collation_pool = [keccak(int_to_big_endian(i)) for i in range(20)]
start_seed = keccak(b'\x00' * 32)


def get_look_ahead_period_length():
    return loog_ahead_period_length


def get_windback_period_length():
    return windback_period_length


def get_eligible_collator(period, shard_id):
    seed = start_seed
    for i in range(period):
        seed = keccak(seed + int_to_big_endian(i))
    
    collator_number = big_endian_to_int(keccak(seed + int_to_big_endian(shard_id))) % len(collation_pool)
    return (
        collator_number,
        collation_pool[collator_number],
    )


def get_collation_head(period, shard_id):
    _, collator_addr = get_eligible_collator(period, shard_id)
    _, prev_collation_addr = get_eligible_collator(period-1, shard_id)

    header = {
        "period": period,
        "shard_id": shard_id,
        "collator": collator_addr,
        "header_hash": keccak(collator_addr + int_to_big_endian(period) + int_to_big_endian(shard_id)),
        "parent_header_hash": keccak(prev_collation_addr + int_to_big_endian(period-1) + int_to_big_endian(shard_id)),
    }
    return header


def add_header(period, shard_id, collator_addr):
    _, eligible_collator_addr = get_eligible_collator(period, shard_id)
    assert collator_addr == eligible_collator_addr
