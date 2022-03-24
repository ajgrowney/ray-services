import json
import logging
import os
import sys
from threading import Thread

from flask import Flask, request, Response
from kafka import KafkaConsumer, KafkaProducer
import wikipedia
from wikipedia import DisambiguationError, PageError
from coreSchemas import ServiceMessage, ServiceMessageContent

KAFKA_HOST = os.getenv("RAY_KAFKA_HOST", "10.0.0.72:9092")
# Logging Configuration
logging_file = os.environ["RAY_ROOT"]+"logs/lookup_api.log"
logFileHandler = logging.FileHandler(logging_file)
logger = logging.getLogger("LookupService")
logger.addHandler(logFileHandler)
logger.setLevel(logging.INFO)

class ServiceMessageContent:
    def __init__(self, msg_json) -> None:
        self.type = msg_json["type"]
        self.parameters = msg_json["parameters"]

class ServiceMessage:
    def __init__(self, msg_json:json) -> None:
        self.content = ServiceMessageContent(msg_json["content"])
        self.context = msg_json["context"]

class LookupService:
    def __init__(self, port:int, kafka_host:str, logger):
        self.kafka_topic = "svc.lookup"
        self.admin_api, self.host, self.port = Flask("Lookup Admin"), "0.0.0.0", port
        self.admin_api.add_url_rule('/health', 'Status Check', self.status, methods=['GET'])
        self.admin_api.add_url_rule('/shutdown', 'shutdown', self.shutdown, methods=['POST'])
        self.serve_api = Thread(target=self.admin_api.run, args=(self.host, self.port), daemon=True)
        self.kafka_consumer = KafkaConsumer(self.kafka_topic, group_id='consumer_svc', auto_offset_reset='earliest',
                                    bootstrap_servers=[kafka_host], api_version=(0, 10), consumer_timeout_ms=1000)
        self.kafka_producer = KafkaProducer(bootstrap_servers=[kafka_host], api_version=(0,10))
        self._logger = logger
        self._exit = False

    def response_handler(self, msg_id, result, context):
        """
        :param: result { dict } - Results from a todo service function
        :param: context { dict } - Context from a service command/request
        """
        if context["source"] == "client":
            msg_key = bytes(msg_id, encoding="utf-8")
            message = {"content": {"type": "services.event", "parameters": {"message_id": msg_id, "svc_response": result}}, "context": {"source": "service.lookup"}}
            msg_value = bytes(json.dumps(message), encoding="utf-8")
            self.kafka_producer.send("core.client-mgr", key=msg_key, value=msg_value)
        else:
            self._logger.info(f"Result: {result}")
            self._logger.info(f"Context: {context}")
        return

    def summarize(self, article, sentence_limit:int = None):
        self._logger.info("Summarize Request | %s, %s", article, sentence_limit)
        try:
            if(sentence_limit):
                summary = wikipedia.summary(article, sentences=sentence_limit)
            else:
                summary = wikipedia.summary(article)
            self._logger.debug(f"Article {article} had summary {summary}")
            return { "results": [str(summary)], "errors": [] }
        except DisambiguationError as e:
            return { "errors": [e.options]}
        except PageError as e:
            return { "errors": ["Does not match any pages"]}

    def message_handler(self, msg_key:str, msg:ServiceMessageContent):
        """Handle topic messages
        :param: msg_key { identifier } - identifier for the message
        :param: 
        """
        msg_type_map = {
            "topic.summarize": self.summarize,
            "system.status": self.status
        }
        if msg.type not in msg_type_map.keys():
            return {"result": None, "errors": [f"type {msg.type} does not exist"]}
        self._logger.info("MessageHandler | TypeExists | %s %s", msg.type, msg.parameters)
        result = msg_type_map[msg.type](**msg.parameters)
        self._logger.info("MessageHandler | Results | %s", result)
        self._logger.info(f"Key: {msg_key}, Result: {result}")
        return result

    def run(self):
        self.serve_api.start()
        while not self._exit:
            for msg in self.kafka_consumer:
                self._logger.info("Got Message")
                try:
                    msg_key = msg.key.decode("utf-8")
                    msg = ServiceMessage(json.loads(msg.value.decode("utf-8")))
                    res = self.message_handler(msg_key, msg.content)
                    self.response_handler(msg_key, res, msg.context)
                except Exception as e:
                    self._logger.error(f"Failed to process message: {e}")

    def status(self):
        return { "status": 200 }

    def shutdown(self):
        self._exit = True
        return { "status": 204 }

if __name__ == "__main__":
    service_port = sys.argv[1] if len(sys.argv) == 2 else 5000
    logger.info("Starting Service")
    lookup_svc = LookupService(service_port, KAFKA_HOST, logger)
    lookup_svc.run()