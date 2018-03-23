import asyncio
import logging
from collections import namedtuple


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


async def collator(shard_id, messages_in, smc):
    logger = logging.getLogger("collator")

    while True:
        period = smc.period
        message = await messages_in.get()
        if message[0] == "newProposal":
            proposal = message[1]
            logger.info("accepting proposal for period {} by proposer {}".format(
                proposal.period,
                proposal.proposer
            ))
            smc.collation_headers[shard_id].append(proposal)
            smc.period += 1


address = 0
messages = asyncio.Queue()
smc = SMC(1)


loop = asyncio.get_event_loop()
loop.create_task(collator(0, messages, smc))
loop.create_task(proposer(0, address, messages, smc))
loop.run_forever()
