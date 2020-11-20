import cv2
import os
import numpy as np
import sys
from constants import face_detector as faceCascade, TRAINING_DATA_DIR
RAW_DATA_DIR = "./data/raw"
RAW_FACES_LOC = "/".join([RAW_DATA_DIR,"faces"])
RAW_IMAGES_LOC = "/".join([RAW_DATA_DIR,"full_images"])

def label_raw_faces(source_dir:str, destination_dir:str):
    files = os.listdir(source_dir)
    for f in files:
            img_src_path = "/".join([source_dir,f])
            
            selected_img = cv2.imread(img_src_path) 
            cv2.imshow(f,selected_img)
            while True:
                k = cv2.waitKey(30) & 0xff
                if k == 27: # press 'ESC' to quit
                    break
            cv2.destroyAllWindows()
            label = input("Label: ")
            if not os.path.exists("/".join([destination_dir,label])):
                os.makedir("/".join([destination_dir,label]))
            os.rename(img_src_path,"/".join([destination_dir,label,f]))

    return

# Walk the raw images directory
def prepare_training_data(source_dir:str, destination_dir:str):
    for root, names, files in os.walk(source_dir):
        for f in files:
            img_path = "/".join([root,f])
            img = cv2.imread(img_path)

            img = cv2.flip(img, 1)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(20, 20)
            )
            img_face_count = 0
            for (x,y,w,h) in faces:
                roi_color = img[y:y+h, x:x+w]
                img_dest_path = "/".join([destination_dir,str(img_face_count)+"_"+f])
                cv2.imwrite(img_dest_path,roi_color)
                img_face_count += 1
    return

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prepare_training_data(RAW_IMAGES_LOC,RAW_FACES_LOC)
    elif cmd == "label":
        label_raw_faces(RAW_FACES_LOC, TRAINING_DATA_DIR)