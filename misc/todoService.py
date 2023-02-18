import uuid
import sys
import os
import time
import json
import logging
from typing import List
from unittest import result
import requests
from threading import Thread
from flask import Flask, request, Response
from kafka import KafkaConsumer, KafkaProducer
import mysql.connector

from schemas.core import ServiceMessage, ServiceMessageContent

KAFKA_HOST = os.getenv("RAY_KAFKA_HOST", default="10.0.0.72:9092")
DB_HOST = os.getenv("RAY_SVC_DB_HOST", "10.0.0.72")
DB_PORT = 3306
DB_USER = os.getenv("RAY_SVC_TODO_USER", "svc_todo")
DB_PASSWD = os.getenv("RAY_SVC_TODO_PWD")
LOG_FILE = os.environ["RAY_ROOT"]+"logs/todo_svc.log"

logger = logging.getLogger("TodoService")
logger.addHandler(logging.FileHandler(filename=LOG_FILE))
logger.setLevel(logging.DEBUG)

class RayTable:
    @classmethod
    def _db_list(cls, db_conn, where:str = None) -> list:
        if where is not None:
            where_clause = f"WHERE {where}"
        else:
            where_clause = ""
        q = f"SELECT {','.join(cls.list_columns)} FROM {cls.table} {where_clause};"
        with db_conn.cursor() as curs:
            curs.execute(q)
            res = [cls(**dict(zip(cls.list_columns, list(r)))) for r in curs]
        return res
    
    @classmethod
    def _db_get(cls, db_conn, id) -> list:
        q = f"SELECT {','.join(cls.get_columns)} FROM {cls.table} WHERE id = {id};"
        with db_conn.cursor() as curs:
            curs.execute(q)
            res = cls(**dict(zip(cls.get_columns, list(curs.fetchone()))))
        return res

    @classmethod
    def _db_insert(cls, db_conn, **kwargs):
        holders = ','.join(['%s' for _ in range(len(cls.insert_columns))])
        q = f"INSERT INTO {cls.table}({','.join(cls.insert_columns)}) VALUES({holders});"
        with db_conn.cursor() as curs:
            curs.execute(q, [kwargs[c] for c in cls.insert_columns])
            id = curs.lastrowid
            db_conn.commit()
        return id


class TodoTask(RayTable):
    list_columns = ["id","title","description"]
    get_columns = ["id", "title", "description"]
    insert_columns = ["title", "description"]
    table = "tasks"
    def __init__(self, **kwargs) -> None:
        self.id = kwargs["id"]
        self.title = kwargs["title"]
        self.description = kwargs["description"]


class TodoTaskInstance(RayTable):
    def __init__(self, **kwargs) -> None:
        self.id = kwargs["id"]
        self.task = kwargs["task"]
        self.sequence_id = kwargs["sequence_instance"]
        self.completed = kwargs["completed"]

class TodoSequence(RayTable):
    list_columns = ["id","title","description"]
    get_columns = ["id","title","description", "dag"]
    table = "sequences"
    def __init__(self, **kwargs) -> None:
        self.id = kwargs["id"]
        self.title = kwargs["title"]
        self.description = kwargs["description"]

        # Lower Level Definition
        dag = kwargs.get("dag")
        if dag:
            self.dag = json.loads(dag)
            self._links = [{"rel": "task", "href": f"/tasks/{k}" } for k in self.dag.keys()]

class TodoSequenceStatus(RayTable):
    table = "sequenceStatuses"
    def __init__(self, **kwargs) -> None:
        self.id = kwargs["id"]
        self.title = kwargs["title"]

class TodoSequenceInstance(RayTable):
    table = "sequenceInstances"
    def __init__(self, **kwargs) -> None:
        self.id = kwargs["id"]
        self.sequence = kwargs["sequence"]
        self.dag = kwargs["dag"]
        self.status = kwargs["status"]

class TodoSequenceSchedule(RayTable):
    list_columns    = ["id", "sequence", "active", "schedule", "conditional"]
    get_columns     = ["id", "sequence", "active", "schedule", "conditional"]
    table = "sequenceSchedules"
    def __init__(self, **kwargs) -> None:
        self.id = kwargs.get("id")
        self.sequence = kwargs.get("sequence")
        self.active = kwargs.get("active")
        self.schedule = kwargs.get("schedule")
        self.conditional = kwargs.get("conditional")


class MySQLStore:
    def __init__(self, host, port, user, password, db:str = 'todo') -> None:
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.db_conn = mysql.connector.connect(
            host=host, port=port, user=user, password=password, database=db)
    
    def close_conn(self):
        self.db_conn.close()

    def create_task(self, title:str, description:str, init_instance:bool = True) -> int:
        """Create a task"""
        return TodoTask._db_insert(self.db_conn, title=title, description=description)
    
    def create_task_schedule(self, task:int, active:bool, schedule:str, condition:str) -> bool:
        """Create a task schedule
        :param task {int}: Task id
        :param active { bool }: Whether the scheduler will actively create instances per condition
        :param schedule { str }: Cron Format
        :param condition { str }: Extra criteria whether to run it or not
        """
        q = "INSERT INTO taskSchedules(task, active, schedule, `condition`) VALUES (%s,%s,%s,%s);"
        curs = self.db_conn.cursor()
        curs.execute(q, (task, active, schedule, condition))
        self.db_conn.commit()
        return

    def init_task_instance(self, task:int, seq_inst_id:int = None, completed:bool = False) -> bool:
        """
        """
        q = "INSERT INTO taskInstances(task, sequence_instance, completed) VALUES (%s,%s,%s);"
        curs = self.db_conn.cursor()
        curs.execute(q, (task, seq_inst_id, completed))
        self.db_conn.commit()
        return True
    
    def get_tasks(self, ids) -> List[TodoTask]:
        """
        """
        tasks = []
        for i in ids:
            tasks.append(TodoTask._db_get(self.db_conn, i))
        return tasks
    
    def list_tasks(self, where:str = None) -> list:
        """List tasks
        """
        return TodoTask._db_list(self.db_conn, where)

    def list_task_instances(self, incomplete_only:bool = False) -> List[TodoTaskInstance]:
        """List task instances
        """
        q = """
        SELECT t.title, t.description, ti.sequence_instance, ti.completed, ti.created_at
        FROM taskInstances ti
        INNER JOIN tasks t on t.id = ti.task
        """
        if incomplete_only:
            q += " WHERE ti.completed = false"
        q += ";"
        curs = self.db_conn.cursor()
        curs.execute(q)
        res = [r for r in curs]
        curs.close()
        return res

    def list_sequences(self, where:str = None) -> List[TodoSequence]:
        """List sequences
        """
        return TodoSequence._db_list(self.db_conn, where)

    def list_sequence_schedules(self, where:str = None) -> List[TodoSequenceSchedule]:
        """List sequence schedules
        """
        return TodoSequenceSchedule._db_list(self.db_conn, where)

    def get_sequence(self, seq_id) -> TodoSequence:
        """Read a sequence from db from id
        """
        return TodoSequence._db_get(self.db_conn, seq_id)
        

    def create_sequence(self, init_instance:bool = True) -> bool:
        """
        """
        return
    
    def init_sequence_instance(self, seq_inst_id:str) -> bool:
        """
        """
        return


class TodoService:
    """Manage todo lists, reminders, and calendars
    """
    def __init__(self, port:int, kafka_host:str, storageEngine, logger):
        # API Configuration
        self.server, self.host, self.port = Flask("Todo Service"), "0.0.0.0", port
        self.server.add_url_rule('/health', 'Status Check', self.status, methods=['GET'])
        self.server.add_url_rule('/shutdown', 'shutdown', self.shutdown, methods=['POST'])
        self.serve_api = Thread(target=self.server.run, args=(self.host, self.port), daemon=True)
        # Kafka Configuration
        self.kafka_topic = "svc.todo"
        self.kafka_consumer = KafkaConsumer(self.kafka_topic, group_id='consumer_svc', auto_offset_reset='earliest',
                                    bootstrap_servers=[kafka_host], api_version=(0, 10), consumer_timeout_ms=1000)
        self.kafka_producer = KafkaProducer(bootstrap_servers=[kafka_host], api_version=(0,10))
        # Storage Configuration
        self.store = storageEngine
        self._logger = logger
        self._exit = False

    def response_handler(self, msg_id, result, context):
        """
        :param: result { dict } - Results from a todo service function
        :param: context { dict } - Context from a service command/request
        """
        if context["source"] == "client":
            msg_key = bytes(msg_id, encoding="utf-8")
            message = {"content": {"type": "services.event", "parameters": {"message_id": msg_id, "svc_response": result}}, "context": {"source": "service.todo"}}
            self._logger.info("Sending Message ID %s: %s", msg_id, message)
            msg_value = bytes(json.dumps(message), encoding="utf-8")
            self.kafka_producer.send("core.client-mgr", key=msg_key, value=msg_value)
        else:
            self._logger.info("Result: %s", result)
            self._logger.info("Context: %s", context)
        return

    def list_tasks(self):
        self._logger.debug("list_tasks | Parameters: ")
        try:
            self._logger.info("list_tasks | Listing tasks")
            tasks = self.store.list_tasks()
            json_tasks = [t.__dict__ for t in tasks]
            self._logger.debug("list_tasks | Listed tasks: %s", json_tasks)
            result = {"success": True, "results": json_tasks}
        except Exception as e:
            print(e)
            result = {"success": False, "errors": ["Something went wrong on the database request"]}
        self._logger.debug("list_tasks | Result: %s", result)
        return result

    def create_task(self, title:str, description:str):
        self._logger.debug("create_task | Parameters: title = %s, description=%s", title, description)
        try:
            task_id = self.store.create_task(title, description)
            self._logger.debug("create_task | Created task: %s", task_id)
            result = {"success": True, "results": [task_id]}
        except Exception as e:
            print(e)
            result = {"success": False, "errors": ["Something went wrong on the database request"]}
        self._logger.debug("create_task | Result: %s", result)
        return result

    def get_tasks(self, task_ids:list):
        self._logger.debug("get_tasks | Parameters: task_ids = %s", task_ids)
        try:
            tasks = self.store.get_tasks(task_ids)
            json_tasks = [t.__dict__ for t in tasks]
            self._logger.debug("get_tasks | Found tasks: %s", json_tasks)
            result = {"success": True, "results": json_tasks}
        except Exception as e:
            print(e)
            result = {"success": False, "errors": ["Something went wrong on the database request"]}
        self._logger.debug("list_tasks | Result: %s", result)
        return result

    def get_sequence(self, seq_id):
        try:
            seq = self.store.get_sequence(seq_id)
            result = { "success": True, "results": [seq.__dict__]}
        except Exception as e:
            print(e)
            result = { "success": False, "errors": ["Internal"]}
        return result

    def list_sequences(self, active:bool = False, **kwargs):
        self._logger.debug("list_sequences | Parameters: ")
        try:
            self._logger.info("list_sequences | Listing seq")
            seqs = self.store.list_sequences(**kwargs)
            json_seqs = [s.__dict__ for s in seqs]
            self._logger.debug("list_sequences | Listed seq: %s", json_seqs)
            result = {"success": True, "results": json_seqs}
        except Exception as e:
            print(e)
            result = {"success": False, "errors": ["Something went wrong on the database request"]}
        self._logger.debug("list_sequences | Result: %s", result)
        return result

    def list_sequence_schedules(self, active:bool = False, **kwargs):
        self._logger.debug("list_sequence_schedules | Parameters: ")
        try:
            self._logger.debug(kwargs)
            self._logger.info("list_sequence_schedules | Listing seq")
            seqs = self.store.list_sequence_schedules(**kwargs)
            json_seqs = [s.__dict__ for s in seqs]
            self._logger.debug("list_sequence_schedules | Listed seq: %s", json_seqs)
            result = {"success": True, "results": json_seqs}
        except Exception as e:
            print(e)
            result = {"success": False, "errors": ["Something went wrong on the database request"]}
        self._logger.debug("list_sequence_schedules | Result: %s", result)
        return result

    def fetch_calendars(self):
        return

    def fetch_events(self, calendar_id):
        return

    def upsert_events(self, calendar_id):
        return

    def init_sequence_instance(self, sequence_id:str, ):
        """
        """
        scheduling_id = ""

    def todo_scheduler(self):
        """Create sequence instance for each sequence 
        that doesn't have an active instance for its timeframe
        """
        # Select all sequences that have a schedule

        # Check for respective scheduled instance of that sequence
        ## If not exist, create a new instance

        return

    def status(self):
        return { "status": 200, "type": "string", "results": ["RUNNING"]}
    
    def message_handler(self, msg_key:str, msg:ServiceMessageContent):
        """Handle topic messages
        :param: msg_key { identifier } - identifier for the message
        :param: 
        """
        msg_type_map = {
            "tasks.list": self.list_tasks,
            "tasks.get": self.get_tasks,
            "tasks.create": self.create_task,
            "sequences.list": self.list_sequences,
            "sequenceSchedules.list": self.list_sequence_schedules,
            "sequences.get": self.get_sequence,
            "sequence.init": self.init_sequence_instance,
            # "events.upsert": self.upsert_events,
            # "calendars.list": self.fetch_calendars,
            "system.status": self.status
        }
        if msg.type not in msg_type_map.keys():
            return {"result": None, "errors": [f"type {msg.type} does not exist"]}
        
        result = msg_type_map[msg.type](**msg.parameters)
        self._logger.info(f"MessageHandler | Key: {msg_key}, Result: {result}")
        return result

    def run(self):
        self.serve_api.start()
        self.todo_scheduler()
        while not self._exit:
            for msg in self.kafka_consumer:
                try:
                    self._logger.info("Received Message")
                    msg_key = msg.key.decode("utf-8")
                    msg = ServiceMessage(json.loads(msg.value.decode("utf-8")))
                    res = self.message_handler(msg_key, msg.content)
                    self.response_handler(msg_key, res, msg.context)
                except Exception as e:
                    print(f"Message processing exception: {e}")
        try:
            self.store.close_conn()
        except:
            print(f"Failed to close connection")

    def shutdown(self):
        try:
            self.store.close_conn()
        except:
            print(f"Failed to close connection")
        return { "status": 200 }


if __name__ == '__main__':
    service_port = 5004
    # store.create_task("Take out trash", "Put the trash can and recycling out on curb", False)
    logger.info("Starting Todo Service")
    TODO_STORE = MySQLStore(DB_HOST, DB_PORT, DB_USER, DB_PASSWD)

    todo_svc = TodoService(service_port, KAFKA_HOST, TODO_STORE, logger)

    message_type = sys.argv[1]
    message_params = json.loads(sys.argv[2])
    message_key = str(uuid.uuid4())
    svc_message = ServiceMessageContent({"type": message_type, "parameters": message_params})
    res = todo_svc.message_handler(message_key, svc_message)
    print(json.dumps(res))
    # todo_svc.run()