from collections import namedtuple


CollationHeader = namedtuple("CollationHeader", [
    "shard_id",
    "proposer",
    "number",
    "period",
])


Collation = namedtuple("Collation", [
    "header",
    "body",
])
