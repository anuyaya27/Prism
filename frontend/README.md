# PRISM Frontend

Minimal React + TypeScript (Vite) UI to call the PRISM backend.

Structure:
- `src/api/client.ts` - simple fetch wrappers with configurable base URL (`VITE_API_BASE_URL`, defaults to `http://127.0.0.1:8000`).
- `src/App.tsx` - single-page experience (prompt, model selection, metrics, synthesis).
- `src/styles.css` - lightweight styling.

Scripts (from `frontend/`):
- `npm install`
- `npm run dev` (http://localhost:5173)
- `npm run build`
- `npm run preview`

Local env:
- Create `.env.local` with `VITE_API_BASE_URL=http://127.0.0.1:8000` (or your backend). Vite reads env at startup, so restart `npm run dev` after changing `.env.local`.
