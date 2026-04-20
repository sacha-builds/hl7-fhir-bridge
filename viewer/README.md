# Viewer

Vue 3 + Vite + TypeScript clinical viewer for the HL7 v2 → FHIR bridge.

## Local development

```bash
cd viewer
npm install
npm run dev
```

The dev server starts on [http://localhost:5173](http://localhost:5173) and expects the bridge on `:8000` and HAPI FHIR on `:8080` (defaults from `.env.example`).

## Build for production

```bash
npm run build
```

Outputs a static bundle in `dist/` ready for Cloudflare Pages, Vercel, or Netlify.

## Scripts

| Command             | Purpose                                   |
| ------------------- | ----------------------------------------- |
| `npm run dev`       | Start Vite dev server with HMR            |
| `npm run build`     | Type-check + production build             |
| `npm run type-check`| Run `vue-tsc` without emitting            |
| `npm run format`    | Format with Prettier                      |
