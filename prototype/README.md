# SwarUtsav ZIP prototype (isolated)

The uploaded `SwarUtsav.zip` contains a separate TanStack Start / React / TypeScript application under `ExQt3OIywpNfC44V-grok-workspace/`. This is **not** a drop-in replacement for the repository's `frontend/` React starter and `backend/` FastAPI service.

The ZIP uses SQL migrations / Postgres-compatible code, Better Auth, and application-defined heuristic scoring. The intended SRS architecture describes FastAPI microservices, DynamoDB, Whisper, Llama 3, and optional MediaPipe/OpenCV. These are not equivalent implementations.

This branch preserves a representative extracted scoring module in `prototype/src/lib/scoring.ts` for comparison and review. It does **not** claim to contain the whole ZIP or a production AI integration. No existing application file was overwritten.

## Safe integration plan

1. Inventory application-owned ZIP files and exclude generated `.grok`, `.vercel`, `.tanstack`, local caches, screenshots and preview artifacts.
2. Decide whether the ZIP's TanStack app replaces the current frontend or remains a separate prototype. Avoid running two incompatible router stacks in one app.
3. Map Postgres migrations to the SRS's DynamoDB data model before connecting persistent data.
4. Replace placeholder/heuristic feedback with actual Whisper, audio analysis and Llama evaluations; treat visual indicators as optional and evidence-based.
5. Add tests for session ownership, scoring, authentication and consent before merging.

**Important:** The scoring code included here is a prototype heuristic and must not be represented as genuine ASR, LLM or video analysis.
