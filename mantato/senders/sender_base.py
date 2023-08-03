from sys import exit
import threading
from shutil import which
import subprocess
import json
from abc import abstractmethod

from mantato.messaging_utils import MessagingEntity, run


class SenderBase(MessagingEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

        # Locate rds_tool
        if not which('ls'):
            exit('rds_tool executable not found in the system. Please install it.')

        self._initialize_connection()
        self._initialize_queues()

        self._update_rt = True

    def run(self):
        self._channel.basic_consume(queue=self._metadata_queue_name, on_message_callback=self.callback, auto_ack=True)
        self._channel.start_consuming()

    @abstractmethod
    def callback(self, ch, method, properties, body):
        pass

    def _initialize_queues(self):
        # Incoming queue settings
        self._propagator_exchange_name = 'propagator_metadata_exchange'
        self._propagator_topic = 'com.metadata.metadata_event'

        self._channel.exchange_declare(exchange=self._propagator_exchange_name, exchange_type='topic')

        # Consider a message not consumed within 10 seconds as invalid
        queue_arguments = \
            {
                'x-message-ttl': 10000
            }

        result = self._channel.queue_declare(queue='', auto_delete=True, arguments=queue_arguments)
        self._metadata_queue_name = result.method.queue
        self._channel.queue_bind(exchange=self._propagator_exchange_name, queue=self._metadata_queue_name,
                                 routing_key=self._propagator_topic)
