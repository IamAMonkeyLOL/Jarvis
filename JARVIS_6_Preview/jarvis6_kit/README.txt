JARVIS 6.0 - OPERATION EVOLUTION / DEVELOPER PREVIEW

IMPORTANT: This is an independent preview app, not a replacement for your existing Jarvis.
Do NOT extract it over jarvis_starter. Do NOT overwrite your original backup.

1. Extract the ZIP to a NEW folder, for example:
   C:\Users\Riley\OneDrive\Desktop\Jarvis\Jarvis-6-Preview
2. Double-click INSTALL_PREVIEW.bat (no admin needed).
3. Ensure Ollama is running and at least one local model is installed.
4. Double-click START_JARVIS_6_PREVIEW.bat.
5. Open http://127.0.0.1:8502 if your browser does not open automatically.

Includes: dark dashboard, Ollama chat, CPU/RAM monitor, read-only SQLite
memory database summary, read-only self-improvement diff viewer.

The preview does not integrate the original app's voice/login/tool stack.
It does not write to your original Jarvis files. It saves chat only in
Streamlit session memory unless you download a chat export yourself.

If you want to inspect existing memory database summaries, COPY the data
folder into this preview folder. Do not move or delete the original.

If the BAT cannot find Python, open PowerShell in this folder and run:
  py -m pip install streamlit psutil
  py -m streamlit run jarvis6_preview.py --server.port 8502
