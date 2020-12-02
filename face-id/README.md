# Face ID Service for Peripherals
Continous recognition system for detecting expected faces

## How to Start
Run: `python3 faceIdService.py {desired_port} false {show_video}`
Command Line Args:
- desired_port {integer} - port you want to open for flask to be reachable (Default: 5020)
- show_video {string} - 'true' if you want to show the live streamed face detection, 'false' if not (Default: False)
- The second command line argument is for running with an integrated control center (Should be false but can be configured)

## Prerequisites
### Folder Structure
- /data
    - /training
    - /raw
        - /full_images
        - /faces
### Data
- Setup your pictures that need to be trained in in your `/data` folder
- For cleaning raw data, have your full images in the `/data/raw/full_images` directory and make a `/data/raw/faces` directory
    - Run: `python data_clean.py prep`
- Setup the training data directory at `/data/training`
- To label the detected faces, run `python data_clean.py label`
    - For each image that pops up, click `esc` and then type in the label to give the user


## Service Interface
### Shutdown
- Request: POST /shutdown
### Health
- Request: GET /health
### Service Discovery
- Request: GET /sd