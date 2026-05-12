# Root Scripts

Repository-level automation scripts.

## Demo Recording

`record_demo.js` uses Playwright to open the service, walk through the main demo flow, and save a video under `demo_videos/`.

```bash
npm run demo:local
npm run demo:record
```

`demo:record` targets https://winwin-compass.vercel.app. Use `DEMO_URL` or `--url=` to override the target.

Generated videos are ignored by Git.
