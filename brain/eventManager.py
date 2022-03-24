import traceback
from cv2 import trace
from kafka import KafkaConsumer, KafkaProducer
from uuid import uuid4
import json
from coreSchemas import ClientEvent, ServiceMessage, ServiceMessageContent

class BrainEventManager:
    def __init__(self, nlu_engine, kafka_host, logger):
        self.exit = False
        self.paused = False
        self._logger = logger
        self.nlu_engine = nlu_engine
        self.kafka_host = kafka_host
        self.kafka_topics = ["nlu_request", "svc.nlu"]
        self.kafka_producer = KafkaProducer(bootstrap_servers=[self.kafka_host], api_version=(0,10))
        
    def send_clients_event_msg(self, message:ClientEvent, client_id):
        """
        :param message: { dict } - Client Message schema
        """
        event_message = {
            "content": {
                "type": "clients.event",
                "parameters": {"client_id": client_id, "event": message.to_client_mgr_schema() }
            },
            "context": { "client_id": client_id }
        }
        msg_key = bytes(str(uuid4()), encoding="utf-8")
        msg_value = bytes(json.dumps(event_message), encoding="utf-8")
        self.kafka_producer.send("core.client-mgr", key=msg_key, value=msg_value)
        return

    def response_handler(self, msg_id, result, context):
        """
        :param: result { dict } - Results from a todo service function
        :param: context { dict } - Context from a service command/request
        """
        if context["source"] == "client":
            msg_key = bytes(msg_id, encoding="utf-8")
            message_params = {"message_id": msg_id, "svc_response": result}
            message = {"content": {"type": "services.event", "parameters": message_params}, "context": {"source": "service.nlu"}}
            msg_value = bytes(json.dumps(message), encoding="utf-8")
            self.kafka_producer.send("core.client-mgr", key=msg_key, value=msg_value)
        else:
            self._logger.info(f"Result: {result}")
            self._logger.info(f"Context: {context}")
        return
    
    def client_input(self, text:str, policies:list, execute:bool = True, context:dict = {}):
        """Handle client input
        """
        self._logger.info("ClientInput | Text: %s", text)
        svc_messages = self.nlu_engine.extract_svc_messages(text, policies)
        self._logger.info("ClientInput | Extracted Service Messages: %s", svc_messages)
        assistant_res = self.nlu_engine.get_assistant_response(text)
        if execute:
            if "client_id" in context.keys():
                client_id = context["client_id"]
                for message in svc_messages:
                    self._logger.info("ClientInput | Sending Message %s as client %s", message, client_id)
                    self.send_clients_event_msg(message, client_id)
            else:
                self._logger.warning(f"Unable to execute resolved service messages")
        self._logger.info("ClientInput | Finished")
        result = { "AssistantResponse": assistant_res, "ServiceMessages": [m.to_client_mgr_schema() for m in svc_messages] }
        return result
    
    def message_handler(self, msg_key:str, msg:ServiceMessageContent, context:dict):
        """Handle topic messages
        :param: msg_key { identifier } - identifier for the message
        :param context: { kwargs } 
        """
        msg_type_map = {
            "message.handle": self.client_input,
            "system.status": self.nlu_engine.status
        }
        if msg.type not in msg_type_map.keys():
            return {"result": None, "errors": [f"type {msg.type} does not exist"]}
        self._logger.info("Type: %s", msg.type)
        self._logger.info("Parameters: %s", msg.parameters)
        self._logger.info("Context: %s", context)
        result = msg_type_map[msg.type](**msg.parameters, context=context)
        self._logger.info(f"Key: {msg_key}, Result: {result}")
        return result

    # ---- Kafka Event Consumer ----
    def kafka_event_consumer(self):
        try:
            self._logger.info("Starting kafka consumer")
            consumer = KafkaConsumer(*self.kafka_topics, group_id='consumer_svc', auto_offset_reset='earliest',
                                    bootstrap_servers=[self.kafka_host], api_version=(0, 10), consumer_timeout_ms=1000)
            self._logger.info("Running Kafka Consumer Thread")
            while not self.exit:
                if not self.paused:
                    for msg in consumer:
                        try:
                            msg_key = msg.key.decode("utf-8")
                            self._logger.info("Got Message Key")
                            msg = ServiceMessage(json.loads(msg.value.decode("utf-8")))
                            self._logger.info("Got Service Message")
                            res = self.message_handler(msg_key, msg.content, msg.context)
                            self._logger.info("Got Message Result")
                            self.response_handler(msg_key, res, msg.context)
                        except BaseException as e:
                            traceback.print_exc()
                            self._logger.error(f"Failed to process message: {e} [{repr(e)}]")
        except Exception as e:
            self._logger.error(f'EventManager | {e}')
        self._logger.info("Done")

 
