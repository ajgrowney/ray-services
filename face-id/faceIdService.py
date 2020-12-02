import numpy as np
import cv2
import json
import datetime
import time
import sys
from threading import Thread
from constants import face_detector as faceCascade, model, model_ids
from flask import Flask, request

app = Flask(__name__)
flask_port = 5020 if len(sys.argv) < 2 else int(sys.argv[1])
init_pause = True if (len(sys.argv) >= 3 and sys.argv[2].lower() == "true") else False
integrated = True if (len(sys.argv) >= 4 and sys.argv[3].lower() == "true") else False
show_video = True if (len(sys.argv) >= 5 and sys.argv[4].lower() == "true") else False

class FaceTracker:
    def __init__(self, run_integrated:bool):
        self.faces = {}
        self.integrated = run_integrated

    def register_instance(self, user, location):
        if(user not in self.faces.keys() and self.integrated):
            print(f"POST to Control Center: {user} detected")
        self.faces[user] = { "location": str(location), "time": datetime.datetime.now() }
        return

    def get_current(self):
        return self.faces


class Recognizer:
    def __init__(self, min_conf:int, paused = False, run_integrated = False, show_video = True):
        self.cam_id = 0
        self.capture_width, self.capture_height = 640, 480
        self.paused, self.exit = paused, False
        self.min_conf = min_conf
        self.face_detector = faceCascade
        self.face_id_model = model
        self.face_id_map = model_ids
        self.tracker = FaceTracker(run_integrated)
        self.show_video = show_video


    def run(self):
        cv2.destroyAllWindows()
        self.cap = cv2.VideoCapture(self.cam_id)
        self.cap.set(3,self.capture_width) # set Width
        self.cap.set(4,self.capture_height) # set Height
        while not self.exit:
            if self.paused:
                time.sleep(1)
            else:
                ret, img = self.cap.read()
                img = cv2.flip(img, 1)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(20, 20))
                
                for (x,y,w,h) in faces:
                    roi_gray = gray[y:y+h, x:x+w]
                    idx,conf_loss = model.predict(roi_gray)
                    if conf_loss <= self.min_conf:
                        user, conf = model_ids[str(idx)], (100-conf_loss)
                        img = cv2.putText(img, user + f" ({conf}%)",(x,y-10),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0))
                        cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
                        self.tracker.register_instance(user,(x,y,x+w,y+h))
    
                if self.show_video:
                    cv2.imshow('Face ID Stream',img)
                    k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
                    if k == 27:
                        break
            
        self.cap.release()
        cv2.destroyAllWindows()

    def set_state(self,pause:bool = True):
        self.paused = pause
    
    def shutdown(self):
        return

r = Recognizer(45, init_pause, integrated, show_video)

@app.route("/faces",methods=["GET"])
def get_current_faces():
    return r.tracker.get_current()

@app.route("/state", methods=["POST"])
def update_state():
    req = request.get_json(force=True)
    if("action" in req.keys()):
        if req["action"] == "pause":
            r.paused = True
        elif req["action"] == "resume":
            r.paused = False
        elif req["action"] == "exit":
            r.exit = True
    return { "status": 202 }

@app.route("/sd", methods=["GET"])
def service_discovery():
    results = []
    for rule in app.url_map.iter_rules():
        print(rule.methods)
        results.append({"endpoint": rule.endpoint, "methods": list(rule.methods) })
    return { "status": 200, "results": results }

@app.route("/health",methods=["GET"])
def health_check():
    return { "status": 200, "results": ["Healthy"] }


if __name__ == "__main__":
    t = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": flask_port})
    t.daemon = True
    t.start()
    r.run()
