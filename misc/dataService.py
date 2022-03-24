import sys
import time
import json
from flask import Flask, request
from coreSchemas import ServiceRequest, ServiceResponse

class DatabaseService:
    def __init__(self, port:int):
        self.server, self.port = Flask("Database Service"), port
        self.server.add_url_rule('/shutdown', 'shutdown', self.shutdown, methods=['POST'])
        self.server.add_url_rule('/health', 'status', self.status, methods=['GET'])

    def status(self):
        return { "status": 204 }

    def run(self):
        self.server.run("0.0.0.0", self.port)

    def shutdown(self):
        return { "status": 200 }


if __name__ == '__main__':
    service_port = sys.argv[1] if len(sys.argv) == 2 else 5004
    db_svc = DatabaseService(service_port)
    db_svc.run()
