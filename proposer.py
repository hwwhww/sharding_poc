import asyncio
import logging
from collections import namedtuple
import time


logging.basicConfig(level=logging.INFO)


Proposal = namedtuple("Proposal", [
    "shard_id",
    "proposer",
    "number",
    "period",
])


Collation = namedtuple("Collation", [
    "shard_id",
    "number",
    "period",
])


class SMC:

    def __init__(self, num_shards):
        self.num_shards = num_shards
        self.collation_headers = {
            shard_id: [Proposal(shard_id, None, 0, 0)]
            for shard_id in range(self.num_shards)
        }
        self.period = 1


async def proposer(shard_id, address, messages_out, smc):
    logger = logging.getLogger("proposer")

    my_proposal = None
    my_collation = None
    last_collation_header = None
    while True:
        await asyncio.sleep(1)

        current_collation_header = smc.collation_headers[shard_id][-1]
        if current_collation_header != last_collation_header:
            # if my last proposal got accepted reveal the corresponding collation
            if current_collation_header.proposer == address:
                assert current_collation_header == my_proposal
                assert my_collation is not None
                logger.info("revealing body for collation #{}".format(my_collation.number))
                await messages_out.put(("revealBody", my_collation))

            # publish proposal for next collation
            my_proposal = Proposal(
                shard_id,
                address,
                current_collation_header.number + 1,
                smc.period
            )
            my_collation = Collation(
                my_proposal.shard_id,
                my_proposal.number,
                my_proposal.period
            )
            logger.info("proposing (shard {}, period {}, number {})".format(
                my_proposal.shard_id,
                my_proposal.number,
                my_proposal.period
            ))
            await messages_out.put(("newProposal", my_proposal))
        last_collation_header = current_collation_header
