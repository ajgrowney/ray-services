# Core / Peripheral Services
Public services that are built to add capabilities to the larger ecosystem

## Brain
1) Recieves text input
2) Resolves service messages
3) Forwards messages to core.client-mgr
      4) Sends to respective services
4) Returns (AssistantResponse, ServiceMessages resolved)
## Local Testing
### Todo Service
- Unit Testing

      Key: Generated UUID
      Value: {"content":{"type":"system.status","parameters":{}},"context":{"source":"console"}}
- Integration Testing (Database)

      Key: Generated UUID
      Value: {"content":{"type":"todo.list","parameters":{}},"context":{"source":"console"}}