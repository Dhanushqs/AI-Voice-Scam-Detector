# Voice Scam Detector: Vercel prototype (audio files)

Upload a short call recording, get a transcript and a scam-risk score.

```
browser (public/index.html)
   -> POST /api/analyze (Vercel Python function)
        -> Groq hosted Whisper (speech-to-text)
        -> rule-based scorer (api/_scorer.py)
   <- JSON: transcript, score, level, reasons
```

Whisper itself can't run on Vercel (size and time limits), so transcription is
done by Groq's free Whisper API. The scorer runs inside the function.

## Deploy

1. Get a free API key at https://console.groq.com (check current free-tier limits there).
2. Push this folder to a GitHub repo.
3. On https://vercel.com click **Add New > Project**, import the repo, keep the defaults.
4. In **Settings > Environment Variables** add `GROQ_API_KEY` = your key, then redeploy.
5. Open the Vercel URL and upload a clip.

Or with the CLI: `npm i -g vercel`, then `vercel`, then `vercel env add GROQ_API_KEY`, then `vercel --prod`.

## Test without a key

The "Score text" box on the page sends text straight to the scorer, so you can
test the rules and the UI before setting up Groq.

## Local run

```
npm i -g vercel
vercel dev
```

## Limits

- Request bodies are capped at about 4.5 MB on Vercel, so use clips of roughly a minute or less (mp3 or m4a are small).
- Rule-based scoring only. Your ML classifier can be added to `api/_scorer.py` later
  (keep it small, since serverless size limits apply) or hosted separately and called from the function.
- Never commit your API key. Use role-played or consented recordings only.
