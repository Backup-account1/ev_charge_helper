# Provider investigation notes

## Malanka

Target web application:

`https://customer.malankabn.by/map`

The page is authenticated. The implementation uses a local Playwright browser state.

Do not put your Malanka username/password in source code.

The adapter currently provides a stable abstraction and a DOM parser configuration point. Because authenticated page structure can change, selectors should be discovered from your current logged-in page rather than guessed.

## Evika

Evika is a Belarus charging network operated by Beltelecom. Its public app listing describes:

- nearest charging-station search;
- charging-session tracking;
- reservation/queue;
- power graph and charging-session details;
- history, notifications and analytics;
- AC and DC charging.

Public map:

`https://evika.by/map/`

The app listing was checked during project preparation. No undocumented private API endpoint is hard-coded here.

For the first integration, use the same Playwright/session-state pattern as Malanka. If an official API becomes available, replace the browser adapter internally without changing the Telegram or estimator layers.

## Adding a provider

Create:

`app/providers/my_provider.py`

Implement:

```python
class MyProvider(ChargingProvider):
    async def list_stations(self) -> list[Station]:
        ...

    async def get_active_session(self) -> ChargingSession | None:
        ...
```

Register it in:

`app/providers/registry.py`

The rest of the application remains unchanged.
