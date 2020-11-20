import cv2
import os
import numpy as np
import json
from PIL import Image
from constants import TRAINING_DATA_DIR
faceCascade = cv2.CascadeClassifier('data/cascades/haarcascade_frontalface_default.xml')
model = cv2.face.LBPHFaceRecognizer_create()


def train():
    faces,ids,metadata = [],[],{}
    users = os.listdir(TRAINING_DATA_DIR)
    for user,user_id in zip(users,range(0,len(users))):
        metadata[user_id] = user
        user_photos_root = "/".join([TRAINING_DATA_DIR,user])
        user_photos = os.listdir(user_photos_root)
        for photo in user_photos:
            photo_path = "/".join([user_photos_root,photo])
            img = Image.open(photo_path).convert("L")
            image_array = np.array(img,"uint8")
            faces.append(image_array)
            ids.append(user_id)

    model.train(faces,np.array(ids))
    model.write("models/model.yml")
    with open("models/ids.json","w") as f:
        json.dump(metadata,f)

    return


if __name__ == "__main__":
    train()