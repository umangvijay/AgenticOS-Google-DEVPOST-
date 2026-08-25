# Pub/Sub Worker Architecture

```mermaid
graph LR
    API[FastAPI] -->|Publish Event| PubSub[Pub/Sub Topic]
    PubSub -->|Push Delivery| WorkerEndpoint[/pubsub/push]
    WorkerEndpoint --> WorkerEngine[Workflow Engine]
    WorkerEngine -->|Execute Task| Agent[Agent]
    WorkerEngine -->|Ack/Nack| PubSub
```
