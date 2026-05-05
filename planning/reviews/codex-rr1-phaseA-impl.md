Implemented RR-1 Phase A deterministic PPTX refresh infrastructure.

Key pieces added:
- `PptxRefreshJob` model
- KPI catalog + formatter/resolver
- PPTX ingestor + token detection
- PPTX token patcher
- `/api/pptx` upload/status/apply/download router
- `/decks` frontend page + API client + nav link
- Backend PPTX refresh tests
- `planning/Review.md` RR-1 Phase A entry
- `backend/pytest.ini` and `.gitignore` guards for Windows runtime/temp dirs

Validation:
- `cd backend && python -m pytest --tb=short -q` passed: **258 tests**
- `cd frontend && cmd /c npx tsc --noEmit` passed
- `cmd /c npx next build` was attempted but blocked by network access to Google Fonts for `Open Sans`; no TypeScript errors were found.

No Anthropic/AI integration was added.