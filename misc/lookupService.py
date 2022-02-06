import json
import logging
import os
import requests
import sys
import wikipedia
from wikipedia import DisambiguationError, PageError
from flask import Flask, request, Response
from serviceBase import ServiceRequest, ServiceResponse

# Logging Configuration
logging_file = os.environ["RAY_ROOT"]+"logs/lookup_api.log"
logFileHandler = logging.FileHandler(logging_file)
logging.basicConfig(level=logging.INFO, handlers=[logFileHandler])
logger = logging.getLogger("LookupApi")

class LookupService:
    def __init__(self, logger, integrated:bool = True):
        self.integrated = integrated
        self._logger = logger
        self._logger.info("Initialized")

    def response_handler(self, response):
        if self.integrated:
            json_response = json.loads(json.dumps(response, default=lambda o: o.__dict__))
            json_response["event"] = "output/text"
            json_response["type"] = "Rasa"
            requests.post("http://localhost:5001/controller/todo/input", json=json_response)
            return Response(json.dumps(json_response), status=200, mimetype='application/json')
        else:
            return Response(json.dumps(response, default=lambda o: o.__dict__), status = response.statusCode, mimetype="application/json")

    def summarize(self, article, sentence_limit:int = None):
        try:
            if(sentence_limit):
                summary = wikipedia.summary(article, sentences=sentence_limit)
            else:
                summary = wikipedia.summary(article)
            response = ServiceResponse(200, "string", ["Wikipedia says "+str(summary)])
            return self.response_handler(response)
        except DisambiguationError as e:
            return { "error": [e.options]}
        except PageError as e:
            return { "error": ["Does not match any pages"]}

    def status(self):
        return { "status": 200 }

    def shutdown(self):
        return { "status": 204 }


lookup_api = Flask(__name__)
svc = LookupService(logger, True)

@lookup_api.route('/health', methods=['GET'])
def status():
    return svc.status()

@lookup_api.route('/shutdown', methods=['POST'])
def shutdown():
    return svc.shutdown()

@lookup_api.route('/lookup/summary', methods=['POST'])
def page():
    logger.info("Looking up page")
    json_request = request.get_json(force=True)
    article = json_request['article']
    sentence_limit = request.args.get('limit', default=None)
    return svc.summarize(article, sentence_limit)

if __name__ == "__main__":
    service_port = sys.argv[1] if len(sys.argv) == 2 else 5000
    integrated = bool(sys.argv[2]) if len(sys.argv) >= 3 else True
    lookup_api.run('0.0.0.0', service_port)