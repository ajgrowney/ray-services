import os
import sys
import requests
import json
import logging
from threading import Thread
from kafka import KafkaProducer
KAFKA_HOST = os.getenv("RAY_KAFKA_HOST", default="10.0.0.72:9092")

class CommunicationsManager:
    """ Handle sending messages to the proper client """
    def __init__(self, registered_outputs:list = []):
        log_file = os.environ["RAY_ROOT"] + "logs/communications.log"
        logFileHandler = logging.FileHandler(log_file)
        logging.basicConfig(level=logging.INFO, handlers=[logFileHandler])
        self.logger = logging.getLogger("Coms Manager")
        self.outputs = {}
        for o in registered_outputs:
            self.outputs[o.id] = o
        self.exit = False
        self.paused = False
        self.queue = []
        self.kp = KafkaProducer(bootstrap_servers=[KAFKA_HOST], api_version=(0,10))
        self.event_thread = Thread(target=self.event_loop, daemon=True)
        self.event_thread.start()
    
    def add_output(self, new_output):
        """ Attempt to add an available output client """
        if new_output.id not in self.outputs.keys():
            self.outputs[new_output.id] = new_output
            return True
        else:
            return False
    
    def append_message(self, message, context):
        self.queue.append((message, context))
    
    def event_loop(self):
        while not self.exit:
            if not self.paused:
                while len(self.queue) > 0:
                    m, ctx = self.queue.pop(0)
                    self.handle_message(m, ctx)
    
    def handle_message(self, msg, context):
        if "output_id" in context.keys():
            self.logger.info(msg, context, context["output_id"])
        else:
            self.logger.info(msg, context)