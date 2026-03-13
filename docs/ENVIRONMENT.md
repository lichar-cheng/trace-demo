# Environment Variables

Use a local `.env` file based on `.env.example`. Do not commit the real `.env`.

Main variables:

- `APP_LOGIN_USERNAME`
- `APP_LOGIN_PASSWORD`
- `APP_SECRET_KEY`
- `COLLECT_AUTH_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `NOTION_API_TOKEN`
- `NOTION_DATA_SOURCE_ID`
- `NOTION_DATABASE_ID`
- `NOTION_VERSION`
- `YOUTUBE_API_KEY`
- `YOUTUBE_CHANNEL_IDS`
- `YOUTUBE_PROXY_HTTP`
- `YOUTUBE_PROXY_HTTPS`
- `YOUTUBE_AUDIO_DIR`
- `YOUTUBE_TRANSCRIBE_DIR`
- `WHISPER_MODEL_SIZE`
- `WHISPER_LANGUAGE`
- `WHISPER_DEVICE`
- `WHISPER_COMPUTE_TYPE`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `ANTHROPIC_API_KEY`
- `DATA_ROOT_DIR`

Notes:

- `backend/services/youtube/config.py` already reads YouTube and Whisper settings from env.
- `backend/app.py.txt` reads login, collect token, and app secret from env.
- The repository currently does not have a full LLM provider integration path yet, but the provider keys are listed here so they stay out of source code.
