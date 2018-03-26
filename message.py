from collections import namedtuple


CollationHeader = namedtuple("CollationHeader", [
    "shard_id",
    "proposer",
    "number",
    "period",
    "hash",
])


Collation = namedtuple("Collation", [
    "header",
    "body",
])


def create_genesis_header(shard_id):
    return CollationHeader(
        shard_id=shard_id,
        proposer=None,
        number=-1,
        period=-1,
        hash="00" * 8,
    )
