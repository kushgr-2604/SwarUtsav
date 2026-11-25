# Troubleshooting: microphone and screen recording not visible

## Where to find controls

1. Log into the SwarUtsav React application.
2. Open **AI mock interview** in the left sidebar.
3. On the interview setup page, the **Microphone & Screen recording** device-check panel appears before **Begin practice**.
4. Click **Test microphone** and grant permission. You should see **Ready ✓** when permission succeeds; the test does not save audio.
5. Click **Test screen sharing** and select a window, tab, or screen in the browser chooser. You should see **Ready ✓** when successful; the test does not capture a recording.
6. Choose your role/difficulty/question count and click **Begin practice**.
7. Inside the question panel, use **Dictate answer** or **Whisper spoken answer**. For screen recording, check **I consent to optional recording and uploads** and click **Record screen**.
8. When done, click **Stop screen recording**, then **Download** or **Upload privately**. Stop ongoing camera/screen recording before finishing the interview.

Note: Browser dictation depends on browser support. Whisper transcription additionally requires the backend optional model installation and `ENABLE_WHISPER=true`.

## Deployment

The GitHub repository being updated is `kushgr-2604/SwarUtsav`. **A merged commit is not an automatic redeploy.** If your website is running from another repository, Replit project, manually uploaded frontend, or an old container image, these controls will not appear there.

For the repository's local Docker deployment:

```bash
git pull origin main
docker compose up --build -d
```

If this branch is still under review, check out its feature branch or merge its PR first. Rebuild the frontend image because React code is compiled at image-build time. Refresh the page (hard reload if necessary).

**Compatibility:** Use `https://` or `http://localhost`. The permission prompts must be invoked from a user click. Modern desktop Chrome/Edge are the easiest browsers to test first. Screen/window system audio is browser-dependent.

**Privacy:** Camera/microphone capture and screen recording require explicit permissions. The test card never saves media; actual recordings are local until uploaded by the user. Recording uploads need an authenticated interview, and backend storage in this project is not production hardened.
