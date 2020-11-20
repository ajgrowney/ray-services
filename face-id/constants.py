import cv2
import json

face_detector = cv2.CascadeClassifier('models/cascades/haarcascade_frontalface_default.xml')
model = cv2.face.LBPHFaceRecognizer_create()
model.read("models/model.yml")
with open("models/ids.json") as f:
    model_ids = json.load(f)

TRAINING_DATA_DIR = "./data/training"