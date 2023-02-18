from enum import Enum
import json
from requests.models import Response

class ServiceStatus(Enum):
    initializing = "INITIALIZING"
    processing = "PROCESSING"
    sleeping = "SLEEPING"
    available= "AVAILABLE"
    ext = "EXITING"

class ServiceRequest:
    def __init__(self, method: str, path: str, params: dict):
        self.method = method
        self.path = path
        self.parameters = params
    
def ParseServiceResponse(res):
    if type(res) != Response:
        return None
    else:
        json_res = res.json()
        sr = ServiceResponse(json_res['statusCode'], json_res['returnType'], json_res['response'], json_res['responseOptions'])
        return sr

class ServiceResponse:
    def __init__(self, code = 500, returntype= "", responseobject = None, options = {}):
        # 200: OK Reponse, actions finished
        # 300: Multiple choice, user must provide response with continued actions
        # 400: Error Response, request wasn't mapped to a proper option
        # 500: Internal Error, something went wrong on the internals
        self.statusCode = code

        # Type of response object coming back
        self.type = returntype
        # Should have a defined __str__ function to print the response
        self.results = responseobject
        
# ---- NEW ----

class ServiceMessageContent:
    def __init__(self, msg_json) -> None:
        self.type = msg_json["type"]
        self.parameters = msg_json["parameters"]

class ServiceMessage:
    def __init__(self, msg_json:json) -> None:
        self.content = ServiceMessageContent(msg_json["content"])
        self.context = msg_json["context"]
