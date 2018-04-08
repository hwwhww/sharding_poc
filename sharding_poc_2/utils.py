import logging

from message import (
    CollationHeader,
    Collation,
)

logger = logging.getLogger("utils")


async def receive_and_broadcast_message(node):
    message_queue = node.message_queue
    new_messages = []
    while not message_queue.empty():
        message = message_queue.get_nowait()
        key = None

        header = None
        if isinstance(message, CollationHeader):
            key = message.hash
            header = message
        elif isinstance(message, Collation):
            key = message.header.hash
            header = message.header
        if key not in node.message_logs:
            node.message_logs[key] = message
            new_messages.append(message)
            # if node.node_id.startswith('collator'):
            #     logger.info('Node {} is helping to broadcast message {}'.format(
            #         node.node_id,
            #         message,
            #     ))
            await node.input.put(message)
        # else:
            # logger.info('Receiveds the same message again: {}'.format(message))
    return new_messages