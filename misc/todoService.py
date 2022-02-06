import sys
import time
import json
import requests
from threading import Thread
from flask import Flask, request, Response
from serviceBase import ServiceRequest, ServiceResponse
from kafka import KafkaConsumer, KafkaProducer

class RemindersEngine:
    def __init__(self, _config):
        self.config = _config

todo_server = Flask("Todo Service")


class DjangoStore:
    def __init__(self, protocol, host, port) -> None:
        self._protocol = protocol
        self._port = port
        self.base_url = f"{protocol}://{host}:{port}"
    
    def select(self, table, filter:str = ""):
        """Select data from table
        """
        url = f"{self.base_url}/{table}"
        res = requests.get(url)
        return res
    
class ServiceMessageContent:
    def __init__(self, msg_json) -> None:
        self.type = msg_json["type"]
        self.parameters = msg_json["parameters"]

class ServiceMessage:
    def __init__(self, msg_json:json) -> None:
        self.content = ServiceMessageContent(msg_json["content"])
        self.context = msg_json["context"]

class TodoService:
    """Manage todo lists, reminders, and calendars
    """
    def __init__(self, port:int, kafka_host:str, storageEngine):
        self.server, self.host, self.port = Flask("Todo Service"), "0.0.0.0", port
        self.server.add_url_rule('/health', 'Status Check', self.status, methods=['GET'])
        self.server.add_url_rule('/shutdown', 'shutdown', self.shutdown, methods=['POST'])
        self.serve_api = Thread(target=self.server.run, args=(self.host, self.port), daemon=True)
        self.kafka_consumer = KafkaConsumer('svc.todo', group_id='consumer_svc', auto_offset_reset='earliest',
                                    bootstrap_servers=[kafka_host], api_version=(0, 10), consumer_timeout_ms=1000)
        self.kafka_producer = KafkaProducer(bootstrap_servers=[kafka_host], api_version=(0,10))
        # self.server.add_url_rule('/todo/calendars', TODO , methods=['GET'])
        # self.server.add_url_rule('/todo/calendars/<calendar_id>/events', TODO , methods=['GET'])
        # self.server.add_url_rule('/todo/calendars/<calendar_id>/events', TODO , methods=['PUT', 'POST'])
        self.store = storageEngine
        self._exit = False
        self.integrated = False

    def response_handler(self, msg_id, result, context):
        """
        :param: result { dict } - Results from a todo service function
        :param: context { dict } - Context from a service command/request
        """
        if self.integrated:
            json_response = json.loads(json.dumps(result, default=lambda o: o.__dict__))
            json_response["event"] = "output/text"
            json_response["type"] = "Rasa"
            requests.post(self.controller_input_url, json=json_response)
            return Response(json.dumps(json_response), status = 200, mimetype="application/json")
        else:
            if context["source"] == "client":
                msg_key = bytes(msg_id, encoding="utf-8")
                message = {"content": {"type": "services.event", "parameters": {"message_id": msg_id, "svc_response": result}}, "context": {"source": "service.todo"}}
                msg_value = bytes(json.dumps(message), encoding="utf-8")
                self.kafka_producer.send("core.client-mgr", key=msg_key, value=msg_value)
            else:
                print(result, context)
            return

    def morning(self):
        morning_greeting = "Good morning, sir."
        cur_time = time.strftime("%-I:%M %p")
        morning_time = "The time is " + cur_time

        full_result = " ".join([morning_greeting, morning_time])
        response = ServiceResponse(200, "string", [full_result])
        return self.response_handler(response)

    def list_reminders(self):
        reminders_db = self.store.select("todo/reminders")
        result = {"results": None, "errors": None}
        if reminders_db.status_code == 200:
            response = reminders_db.json()
            results = response["Results"]
            result["results"] = results
        elif reminders_db.status_code == 404:
            result["errors"] = ["It appears as if the database is not reachable"]
        else:
            result["errors"] = ["Something went wrong on the database request"]

        return result

    def fetch_calendars(self):
        return

    def fetch_events(self, calendar_id):
        return

    def upsert_events(self, calendar_id):
        return

    def status(self):
        return { "status": 200, "type": "string", "results": ["RUNNING"]}
    
    def message_handler(self, msg_key:str, msg:ServiceMessageContent):
        """Handle topic messages
        :param: msg_key { identifier } - identifier for the message
        :param: 
        """
        msg_type_map = {
            "tasks.list": self.list_reminders,
            "events.upsert": self.upsert_events,
            "events.list": self.list_reminders,
            "calendars.list": self.fetch_calendars,
            "system.status": self.status
        }
        if msg.type not in msg_type_map.keys():
            return {"result": None, "errors": [f"type {msg.type} does not exist"]}
        
        result = msg_type_map[msg.type](**msg.parameters)
        print(f"Key: {msg_key}, Result: {result}")
        return result

    def run(self):
        self.serve_api.start()
        while not self._exit:
            for msg in self.kafka_consumer:
                try:
                    msg_key = msg.key.decode("utf-8")
                    msg = ServiceMessage(json.loads(msg.value.decode("utf-8")))
                    res = self.message_handler(msg_key, msg.content)
                    self.response_handler(msg_key, res, msg.context)
                except Exception as e:
                    print(f"Message processing exception: {e}")

    def shutdown(self):
        return { "status": 200 }


if __name__ == '__main__':
    service_port = sys.argv[1] if len(sys.argv) == 2 else 5004
    kafka_host = "10.0.0.72:9092"
    store = DjangoStore("http", "localhost", 8000)
    todo_svc = TodoService(service_port, kafka_host, store)
    todo_svc.run()