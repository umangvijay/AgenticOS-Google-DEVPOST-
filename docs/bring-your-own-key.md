# Bring your own Gemini key

1. Create a key in Google AI Studio.
2. In AgentOS open **Settings** → **Your Gemini API key**, or **Vault** with name `gemini` and field `api_key`.
3. The value is encrypted (AES-256-GCM) and never returned by the API.
4. Workflows, MCP builds, debug, and generate load `cred:gemini` for that user and pass it to the Gemini client.

If no user key is stored, AgentOS uses the server `GEMINI_API_KEY` from `.env`.
