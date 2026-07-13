# AI College Notes Assistant

Upload your notes (PDF, DOCX, or TXT) and:
- Get them rewritten as clear, simple study notes
- Ask questions about them in a chat interface
- Generate a multiple-choice quiz to test yourself

Built with Streamlit + Google Gemini.

## 1. Get a Gemini API key

Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create a free key.

**Important:** if you previously shared a key anywhere public (chat, GitHub, screenshots), delete it from AI Studio and generate a new one — old keys should be treated as compromised.

## 2. Run locally

```bash
git clone https://github.com/kiruthiga-07/AI-College-Notes-Assistant.git
cd AI-College-Notes-Assistant
pip install -r requirements.txt
```

Create a folder `.streamlit/` and inside it a file `secrets.toml`:

```toml
GEMINI_API_KEY = "your-real-key-here"
```

Then run:

```bash
streamlit run app.py
```

## 3. Deploy on Streamlit Cloud

1. Push this code to your GitHub repo (do **not** push `secrets.toml` — it's in `.gitignore`).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at your repo and `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your-real-key-here"
   ```
4. Save and reboot the app.

## Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'google.generativeai'` | `requirements.txt` missing/outdated | Make sure `requirements.txt` is in the repo root and matches the one here |
| App loads but says "No API key found" | Secret not set on Streamlit Cloud | Add `GEMINI_API_KEY` under Settings → Secrets, then reboot the app |
| "Couldn't extract any text" after upload | PDF is scanned/image-based, not real text | Use a text-based PDF, or a DOCX/TXT file instead |
| Quiz fails to parse | Gemini occasionally returns malformed JSON | Click "Generate new quiz" again — the app also tries to auto-recover partial JSON |
| `403` / `PermissionDenied` from Gemini | API key invalid, revoked, or quota exceeded | Generate a fresh key at AI Studio and update your secret |

## File structure

```
app.py                          # Main Streamlit app
requirements.txt                # Python dependencies
.streamlit/secrets.toml.example # Template for your local secret (copy to secrets.toml)
.gitignore                      # Keeps secrets.toml out of git
```
