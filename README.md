# KURIO: Think Through

Daily static knowledge feed from Danish Wikipedia with licensed Wikimedia Commons images.

- At most one new story and four candidate topics per UTC day.
- Scheduled daily at 06:23 UTC; GitHub may delay scheduled jobs.
- Offline tests run before generation. Concurrent jobs are serialized.
- Daily attempt state is committed even if generation fails; manual reruns respect the same quota.
- Each accepted story requires five distinct licensed photographs. Gallery files must also be linked from the source Wikipedia article.
- No paid AI APIs are called. Image selection and sentence extraction are deterministic and still need editorial review.
- The first generated Tornado story was withdrawn after review found irrelevant search images. The stricter gate now rejects those unlinked results. The feed is intentionally empty until a later acceptable generation.

## Cloudflare Pages

Connect this repository with production branch `main`.
Use no framework preset, leave the build command empty, and set the build output directory to `content-engine/site`.
The published feed will be `/feed.json`. Cloudflare setup and the Android app's feed connection are separate tasks and are not yet completed.

## Verification

`python -m pip install requests Pillow`
`python -m unittest discover -s tests -v`

See `content-engine/LICENSES.md` for source attribution.
