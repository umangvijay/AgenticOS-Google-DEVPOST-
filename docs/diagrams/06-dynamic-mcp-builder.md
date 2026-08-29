# Dynamic MCP builder

```mermaid
flowchart TD
  goal[Goal or Create UI] --> exists{Tool exists}
  exists -->|yes| use[Use registered MCP]
  exists -->|no| kind{What did the user provide}
  kind -->|OpenAPI URL| ingest[Fetch or paste spec]
  ingest --> schema[Generate tool schema]
  schema --> probe[Live HTTP probe]
  probe --> register[Register MCP]
  kind -->|HTTP API no spec| sketch[Sketch or Gemini OpenAPI]
  sketch --> schema
  kind -->|Website no API| plan[Plan browser tools]
  plan --> origin[Lock origin]
  origin --> register
  register --> catalog[Available to all agents]
```

HTTP path: OpenAPI, docs URL, or a prompt that sketches a spec. Website path: Playwright tools on one origin. No hidden official API is invented.
