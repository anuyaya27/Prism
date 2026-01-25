# PRISM Frontend

Minimal React + TypeScript (Vite) UI to call the PRISM backend.

Structure:
- `src/api.ts` – simple fetch wrappers with configurable base URL (`VITE_BACKEND_URL`, defaults to `http://localhost:8000`).
- `src/App.tsx` – single-page experience (prompt, model selection, metrics, synthesis).
- `src/styles.css` – lightweight styling.

Scripts (from `frontend/`):
- `npm install`
- `npm run dev` (http://localhost:5173)
- `npm run build`
- `npm run preview`
