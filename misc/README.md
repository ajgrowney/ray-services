# Services
## Service Interface
### Shutdown
- Request: POST /shutdown
### Health
- Request: GET /health


## Client Manager
### Purpose
Hold a memory of clients available with their capabilities and controllable parameters

## Clothing Service
### Statuses
1) Initializing 

## Project Service
### Statuses
1) Initializing: Setting up the service
2) Available: No file is currently loaded up for editing
3) Processing: File is currently loaded and available for editing
4) Sleeping: Service is uninitialized and needs to be restarted

### Members
1) Available Projects

### Paths
1) Open
- Parameters:
    - Project: <int> ID of the project to open up

2) Save

3) Close



### Classes
- Project
    - Id <integer>: identifier for the project
    - Name <string>: Title of the project
    - Type <string>: Type of project (ex: Machine Learning)
    - Language <string>: Language the project is written in (ex: Python)
    - Path <string>: Absolute path to the root of the project (ex: "C:/Users/.../")
    - Structure <dict>: Format of the project
        - Key <string>: filename (ex: main.py)
        - Value <File>: FileObject

- File
    - Id <integer>: identifier for the file
    - Name <string>: filename (ex: )