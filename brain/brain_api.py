import sys
import os
import logging
import time
from threading import Thread, Event
from flask import Flask, request, Response
from knowledgeService import KnowledgeBase
from eventManager import BrainEventManager
from nluEngine import NLUEngine
import json
KAFKA_HOST = os.getenv("RAY_KAFKA_HOST", "10.0.0.72:9092")

# Logging Configuration
logging_file = os.environ["RAY_ROOT"]+"logs/brain_api.log"
logger = logging.getLogger("BrainApi")
logFileHandler = logging.FileHandler(logging_file)
logger.setLevel(level=logging.INFO)
logger.addHandler(logFileHandler)
logging.basicConfig(level=logging.INFO, handlers=[logFileHandler])

# Initialize NLU Enigne
service_port, rasa_port = int(sys.argv[1]), int(sys.argv[2])
nlu_engine = NLUEngine(rasa_port, logger)

knowledge = KnowledgeBase()
eventManager = BrainEventManager(nlu_engine, KAFKA_HOST, logger)
brain_api = Flask("Ray Brain")

# ---- REST API ----
## Description: Simple Health Check for API Availability
@brain_api.route("/health", methods=['GET'])
def health():
    logger.info('Healthcheck')
    nlu_status = nlu_engine.status()
    return { "status": 200, "type": str.__name__, "results": [nlu_status] }

## Description: Recieve input from an HTTP Request
@brain_api.route("/nlu/input", methods=['POST'])
def ingest_input():
    request_data = request.get_json(force=True)
    res = nlu_engine.extract_svc_messages(request_data["message"])
    assist_res = nlu_engine.get_assistant_response(request_data["message"])
    logger.debug(f"Service Msgs: {res}")
    logger.debug(f"Assistant Response: {assist_res}")
    return { "status": 202, "type": str.__name__, "results": ["Accepted input"] }, 202

@brain_api.route("/shutdown", methods=['POST'])
def shutdown():
    eventManager.exit = True
    nlu_engine.shutdown()
    return { "status": 200, "type": str.__name__, "results": ["Shutdown all processes"] }, 200


nlu_engine.run()
event_thread = Thread(target=eventManager.kafka_event_consumer)
event_thread.start()

# api_thread = Thread(target=brain_api.run, args=('0.0.0.0', service_port, ), daemon=True)
# api_thread.start()

if __name__ == "__main__":
    gunicorn_logger = logging.getLogger('gunicorn.error')
    brain_api.logger.handlers = gunicorn_logger.handlers
    brain_api.logger.setLevel(gunicorn_logger.level)
    try:
        brain_api.run('0.0.0.0',service_port)
    except KeyboardInterrupt:
        eventManager.exit = True
        logger.info("Shutdown of Event Manager")