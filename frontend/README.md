# Campus Connect — Frontend Installation Guide

## Prerequisites

Make sure these are installed before starting.

| Tool | Version | Check |
|---|---|---|
| Node.js | 18.x or higher | `node -v` |
| npm | 9.x or higher | `npm -v` |
| Git | any | `git -v` |

---

## Step 1 — Extract the zip

Download `campus-connect-frontend-v3.zip` and extract it. You will get a folder called `cc-v3`.

---

## Step 2 — Copy files into your project

Your project already has a `frontend/` folder from Phase 1. Replace its `src/` folder entirely.
```
Campus-Connect/
  campus-connect/
    backend/          ← leave this alone
    frontend/
      src/            ← DELETE this folder, replace with cc-v3/src/
      .next/          ← delete this too (will be regenerated)
```

In PowerShell:
```powershell
cd campus-connect\frontend
Remove-Item -Recurse -Force src
Remove-Item -Recurse -Force .next
Copy-Item -Recurse "C:\path\to\cc-v3\src" "."
```

---

## Step 3 — Fix postcss.config.mjs

Open `campus-connect\frontend\postcss.config.mjs` and replace the entire content with:
```js
const config = { plugins: { autoprefixer: {} } };
export default config;
```

This removes the broken Tailwind v4 reference that causes the compile error.

---

## Step 4 — Fix next.config.js

Open or create `campus-connect\frontend\next.config.js` and make sure it contains:
```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["three"],
};
module.exports = nextConfig;
```

The `transpilePackages: ["three"]` line is required for Three.js to work with Next.js.

---

## Step 5 — Create .env.local

Inside `campus-connect\frontend\` create a new file called `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## Step 6 — Install dependencies
```powershell
cd campus-connect\frontend
npm install
```

To verify Three.js installed correctly:
```powershell
npm list three
# Should show: three@0.167.x
```

---

## Step 7 — Run the dev server
```powershell
npm run dev
```

Open your browser:
```
http://localhost:3000
```

---

## Available Routes

| URL | Page |
|---|---|
| `localhost:3000` | Landing page |
| `localhost:3000/login` | Login |
| `localhost:3000/register` | Register (3-step) |
| `localhost:3000/dashboard` | Dashboard |
| `localhost:3000/events` | Events list |
| `localhost:3000/events/e1` | Event detail |
| `localhost:3000/events/create` | Create event form |
| `localhost:3000/clubs` | Clubs list |
| `localhost:3000/clubs/c1` | Club detail |
| `localhost:3000/confessions` | Confession wall |
| `localhost:3000/profile` | Profile page |
| `localhost:3000/notifications` | Notifications |
| `localhost:3000/settings` | Settings |
| `localhost:3000/polls` | Polls |
| `localhost:3000/chat` | Random chat |
| `localhost:3000/leaderboard` | Leaderboard |

---

## Running Backend + Frontend Together

Open two PowerShell windows side by side.

**Window 1 — Backend:**
```powershell
cd campus-connect
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Window 2 — Frontend:**
```powershell
cd campus-connect\frontend
npm run dev
```

---

## Troubleshooting

**Cannot find module @tailwindcss/postcss**
→ Replace `postcss.config.mjs` as shown in Step 3.

**ReferenceError: Cannot access 'DashIcon' before initialization**
→ Replace `src/components/layout/Sidebar.tsx` with the latest version from the zip.

**three is not defined / Canvas errors**
→ Make sure `transpilePackages: ["three"]` is in `next.config.js` (Step 4).

**White screen / hydration error**
→ All Three.js components use `dynamic(..., { ssr: false })`. If you added new 3D components, make sure they follow the same pattern.

**Port 3000 already in use**
```powershell
npm run dev -- --port 3001
```

**node_modules issues**
```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item -Recurse -Force .next
npm install
npm run dev
```

---

## Production Build
```powershell
npm run build
npm run start
```
