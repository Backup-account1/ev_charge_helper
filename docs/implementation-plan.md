# Implementation plan

## Phase 1 — working Telegram MVP
- Bot settings.
- Vehicle profiles.
- Connector filtering.
- Location/radius filtering.
- Provider registry.
- SQLite observations.
- Notifications.

## Phase 2 — provider integration
For each provider:
1. Authenticate locally.
2. Inspect network requests in DevTools/Playwright.
3. Prefer an official/public API if documented.
4. Otherwise parse the authenticated UI.
5. Normalize station/session fields.
6. Add provider integration tests using recorded fixtures.

## Phase 3 — charging prediction
- Collect observations every 30–60 seconds.
- Segment sessions.
- Match vehicle model and chemistry.
- Estimate SOC gain and taper.
- Compare predicted vs actual completion.
- Train a model only after enough historical sessions exist.

## Phase 4 — recognition
- Accept front/rear/side car photos.
- Run make/model recognition.
- Store only the result and confidence by default.
- Use recognition as an additional signal rather than a hard requirement.

## Phase 5 — Telegram Mini App
A Mini App can provide:
- map;
- radius slider;
- connector filters;
- station cards;
- live session card;
- charging curve;
- estimated free time.

The existing bot remains the notification/control channel.
