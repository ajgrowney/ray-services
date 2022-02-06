from .serviceBase import ServiceRequest, ServiceResponse, ServiceStatus
import subprocess
import time
import os
import socket


class Project:
    def __init__(self, id:int, name: str, language:str, path:str, runtime:str):
        self._id = id
        self._name = name
        self._language = language
        self._path = path
        self._runtime = runtime
        self._process = None
    
    # Param: { int } - Port to open up for TCP communication
    # Return: { (int, int) } - Process ID
    def open(self, port:int):
        attempts, max_attempts = 0, 5
        portFound = False
        while(not portFound or attempts >= max_attempts):
            print("RUN IT")
            try:
                self._process = subprocess.Popen([self._runtime, self._path+'main.py', str(port)], stdout=subprocess.PIPE)
                processReady = False
                while(not processReady):
                    time.sleep(2)
                    if(self._process.poll() is None):
                        processReady = True
                print("Process is ready")
                self._port = port
                portFound = True
            except OSError as err:
                print("Excepted Error:",err)
                attempts += 1
                if(attempts >= max_attempts):
                    break
                port += 1
        return (self._process.pid, self._port)

    def send(self, parameters):
        print("Send:",parameters)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', self._port))
        accepted = sock.recv(16)
        sock.send(bytes(parameters['message'], 'utf-8'))
        resp = sock.recv(32)
        print("Response: ", resp)
        sock.close()
        return True
    
    def edit(self):

        return

    def close(self):
        listen_exit = self.send({'message': 'exit'})
        if listen_exit:
            os.kill(self._process.pid, 9)
            os.wait()
            return True
        else:
            return False

class ProjectService:
    def __init__(self):
        self._status = ServiceStatus.initializing
        # Initialization
        self._availableProjects = {
            "1": Project(1, "Sample Hello World", "python", "/home/ajgrowney/Code/helloworld/", "python3")
        }
        self._currentProject = None
        self._currentClient = None
        self._status = ServiceStatus.available

    def handleRequest(self, request: ServiceRequest):
        # Handle Service Level Errors
        if self._status != ServiceStatus.available:
            errorMessage = "Error: service is currently "+str(self._status)
            return ServiceResponse(code=400, returntype=(str), responseobject=[errorMessage])
        
        # Handle Request Path Level Errors
        if(request.path == "/project/open"):
            if "project" not in request.parameters:
                return ServiceResponse(code=400, returntype=type(str), responseobject=["Missing parameter: project"])
            elif request.parameters["project"] not in self._availableProjects:
                errorMessage = "Not found: project with id("+request.parameters["project"]+")"
                return ServiceResponse(code=404, returntype=type(str), responseobject=[errorMessage])
            else:
                result_pid, result_port = self.loadProject(request.parameters["project"], request.parameters["port"])
                print("PID:",result_pid, "Port:",result_port)
                print(type(result_pid), type(result_port))
                if(result_pid < 0):
                    result_error = result_port
                    print("Res error:",result_error)
                    return ServiceResponse(code=500, returntype=type(str), responseobject=["Error: loading project - "+result_error])
                else:
                    return ServiceResponse(code=200, returntype=type(str), responseobject=["Success: project loaded - process " + str(result_pid) + " on port " + str(result_port)])

        elif (request.path == "/project/close"):
            if self._currentProject is None:
                return ServiceResponse(code=400, returntype=type(str), responseobject=["Error: No project is open"])
            else:
                closed = self.closeProject()
                if not closed:
                    return ServiceResponse(code=500, returntype=type(str), responseobject=["Error: failed to close project"])
                else:
                    return ServiceResponse(code=200, returntype=type(str), responseobject=["Success: project closed"])
        elif (request.path == "/project/status"):
            if self._status == ServiceStatus.available:
                return ServiceResponse(code=200, returntype=type(str), responseobject=["Available: "+self._currentProject._name])
            else:
                return ServiceResponse(code=200, returntype=type(str), responseobject=["Not available"])

        elif (request.path == "/project/run"):
            try:
                self._currentProject.send(request.parameters)
                return ServiceResponse(code=200, returntype=type(str), responseobject=["Success: project ran"])
            except Exception as e:
                errorMessage = "Error: "+e
                return ServiceResponse(code=500, returntype=type(str), responseobject=[errorMessage])

    # Return: { (int, int) } - Process ID and Port on which the service can communicate with
    def loadProject(self, proj_id:str, proj_port:int) -> bool:
        try:
            self._currentProject = self._availableProjects[proj_id]
            pid, port = self._currentProject.open(proj_port)
            print(pid, port)
            return (pid, port)
        except Exception as e:
            self._currentProject = None
            return (-1, e)

    def runProject(self):
        return

    def closeProject(self) -> bool:
        if(self._currentProject):
            self._currentProject.close()
        self._currentProject = None
        self._status = ServiceStatus.available
        return True