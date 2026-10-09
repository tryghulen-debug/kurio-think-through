# KURIO: Think Through — automatic content engine

This public repository contains only the daily article content engine, not the Android app and not any passwords or signing keys.

- Workflow: `.github/workflows/refresh-feed.yml` — one scheduled run per day with a maximum of one accepted story per UTC day.
- Generated output: `content-engine/site/` — intended as the build-output folder for a Cloudflare Pages project.
- Source: Danish Wikipedia and licensed Wikimedia Commons photographs; no paid generative AI is used.
- Quality gates may skip a day entirely if sufficient licensed visuals or non-repetitive text cannot be found.

## First-time setup

1. Upload *the contents* of the extracted ZIP to the GitHub repository root, retaining the `.github/`, `content-engine/` and `tests/` directories. Do not upload the ZIP itself.
2. In GitHub Actions, approve workflows if prompted. `Settings → Actions → General → Workflow permissions` should allow Read and write permissions for the workflow to commit the generated feed.
3. Add a repository variable named `WIKIMEDIA_USER_AGENT` identifying your app and contact, e.g. `KURIOThinkThrough/1.0 (contact: your-public-contact@example.com)`; do not use a secret password.
4. In GitHub Actions, run the content workflow manually once and review the log.
5. Connect a Cloudflare Pages project to the same repository. Set no framework preset, no build command, and output directory to `content-engine/site`.
6. After a successful deployment, the app's feed URL should be `https://YOUR-PROJECT.pages.dev/feed.json`.

This does NOT ensure premium-quality, verified articles each day. Human review and licensing verification remain advisable. API quotas and free tiers can change.
