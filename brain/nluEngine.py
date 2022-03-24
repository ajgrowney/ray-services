import sys
import os
import json
import requests
import subprocess
from flask import Flask, request
from coreSchemas import ClientEvent


def extract_rule_messages(text_input: str):
    """Transform text into a list of service messages
    :param user_input: { String } - input to be translated to a task
    :return: { list<ClientEvent> } List of service requests (or NoneTypes) to be handled
    """
    messages = []
    user_inputs = text_input.split('and') if ("and" in text_input) else [text_input]
    for user_input in user_inputs:
        msg = None
        if("outfit" in user_input):
            user_input = user_input.replace("outfit", "").strip()
            msg = {"service":"fashion", "type":"outfit.suggestions", "parameters":{}}
        elif("what is " in user_input):
            user_search = user_input.replace("what is ","")
            msg = {"service":"lookup", "type":"topic.summarize", "parameters":{"article": user_search}}
        elif("morning" in user_input):
            msg = { "service": "todo", "type": "routine.morning", "parameters": {} }
        elif("need to do" in user_input):
            msg = { "service": "todo", "type": "tasks.list", "parameters": {} }
        
        if msg is not None:
            messages.append(ClientEvent(msg))
    return messages

def intent_to_svc_requests(intent, entities):
    if(intent['name'] == "start_controller"):
        msgs = [ClientEvent({ "service": "core.service-mgr", "type": "service.status", "params": {"controller_id": e["value"]}}) for e in entities]
        return msgs
    else:
        return []

class NLUEngine:
    def __init__(self, rasa_port:int, logger):
        self.rasa_port, self.rasa_pid = rasa_port, None
        RASA_LOGFILE = os.getenv("RAY_SVC_ROOT") + "out.log"
        self.rasa_entry = ["rasa", "run", "-m", os.environ['RAY_SVC_ROOT']+"brain/nlu/models", "--enable-api", "--log-file", RASA_LOGFILE,"-p"]
        self.rasa_base = "http://localhost:" + str(self.rasa_port)
        self.rasa_webhooks_url = self.rasa_base+"/webhooks/rest/webhook"
        # self.rasa_predict_url = self.rasa_base+"/conversations/user/predict"
        self.rasa_parse_url = self.rasa_base+"/model/parse"
        self._logger = logger
        
    def extract_svc_messages(self, client_msg, policies:list = ["rules","neural"]):
        svc_messages = []
        if "rules" in policies:
            svc_messages += extract_rule_messages(client_msg)
            self._logger.info("NLUEngine | ExtractRuleSvcMessages | Found following messages: %s", [m.to_client_mgr_schema() for m in svc_messages])
        elif "neural" in policies:
            svc_messages += self.extract_neural_messages(client_msg)
            self._logger.info("NLUEngine | ExtractNeuralSvcMessages | Found following messages: %s", [m.to_client_mgr_schema() for m in svc_messages])
        return svc_messages
    

    # Param: msg { String } - User text based input to parse and identify actions
    # Param: return { ServiceResponse } - serialized
    def extract_neural_messages(self, msg):
        try:
            svc_messages = []
            parse_response = requests.post(self.rasa_parse_url, json={"text": msg})
            
            if(parse_response.status_code == 200):
                parsed_json = parse_response.json()
                self._logger.info("Intents: %s ", parsed_json["intent"])
                self._logger.info("Entities: %s", parsed_json["entities"])
                svc_messages = intent_to_svc_requests(parsed_json["intent"], parsed_json["entities"])
        except Exception as e:
            print(f"Exception: {str(e)}")
        
        return svc_messages

    def get_assistant_response(self, msg):
        """ Using the webhooks url, get the assistant's response
        :param msg: { str } - text input
        :response:
        """
        rasa_request = { "message": msg }
        dialogue_response = requests.post(self.rasa_webhooks_url, json=rasa_request)
        self._logger.info(f"NLU Engine | GetAssistantResponse | Rasa: {dialogue_response.json()}")
        return dialogue_response.json()
    
    def domain(self):
        res = requests.get(self.rasa_base+"/domain", headers={"Accept": "application/json"})
        return res.json()

    def status(self):
        return {"pid": self.rasa_pid.pid, "base": self.rasa_base }
    
    def run(self):
        print("RUNNING",flush=True)
        self.rasa_pid = subprocess.Popen(self.rasa_entry + [str(self.rasa_port)], stdout=subprocess.PIPE)
        return self.rasa_pid

    def shutdown(self):
        os.kill(self.rasa_pid.pid, 9)
        return { "status": 200 }


if __name__ == '__main__':
    rasa_port = int(sys.argv[1]) if len(sys.argv) >= 2 else 5009
    nlu_engine = NLUEngine(rasa_port)
    nlu_engine.run()
