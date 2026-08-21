# PII Masking & rehydration proxy for antigravity 

## Objective 

Build a zero-configuration, local reverse proxy daemon bundled inside an Antigravity extension. The daemon intercepts user prompts, file reads, and streamed LLM responses to sanitize Personally Identifiable Information (PII) using GLiNER before payloads leave localhost, and restores original values upon return.

## ARCHITECTURE
1. Local Daemon (Python / ONNX / FastAPI):
   - Runs silently on `127.0.0.1:8765`.
   - Uses `urchade/gliner_multi_pii-v1` (or ONNX equivalent) on CPU.
   - Maintains an in-memory session Vault: `{"Real Name": "[PERSON_1]"}` and Reverse Vault: `{"[PERSON_1]": "Real Name"}`.
   - Exposes Gemini API-compatible endpoints (`/v1beta/models/...:generateContent` and `:streamGenerateContent`).
   
2. Request Interception Pipeline:
   - Parse inbound JSON payload (`contents.parts[].text`).
   - Run GLiNER extraction for labels: `["person", "email", "phone number", "address", "organization"]`.
   - Replace sensitive spans with consistent deterministic tokens (e.g., `[PERSON_1]`, `[EMAIL_1]`).
   - Forward sanitized JSON to `https://generativelanguage.googleapis.com` via TLS.

3. Response Streaming Pipeline:
   - Receive Server-Sent Events (SSE) / JSON chunks from Google Cloud.
   - Perform string buffer substitution against the Reverse Vault.
   - Stream rehydrated chunks back to Antigravity's UI / webview renderer.

4. Extension Lifecycle (extension.ts):
   - On `activate()`: Spawn daemon binary via `child_process.spawn`.
   - Update workspace global settings: set the API Base URL to `http://127.0.0.1:8765`.
   - On `deactivate()`: Terminate daemon process cleanly.

Auto-Configuration: When activated, the extension sets Antigravity's http.proxy or custom API Base URL setting to point to the local port 127.0.0.1:8080.
EXAMPLE
```
// Inside extension.ts (runs automatically on activate)
import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';

export async function activate(context: vscode.ExtensionContext) {
  // 1. Automatically launch the bundled GLiNER daemon binary in the background
  const binaryPath = path.join(context.extensionPath, 'bin', 'pii-shield-daemon');
  const serverProcess = spawn(binaryPath, ['--port', '8080']);

  // 2. Programmatically redirect the endpoint / base URL setting to localhost
  const config = vscode.workspace.getConfiguration();
  
  // Set configuration target to Global (User level) so it applies everywhere
  await config.update(
    'antigravity.apiBaseUrl',        // or the specific model provider endpoint key
    'http://127.0.0.1:8080/v1', 
    vscode.ConfigurationTarget.Global
  );

  // 3. Show a friendly notification so they know they are protected
  vscode.window.showInformationMessage('🛡️ NGO Privacy Shield is active. PII will be masked automatically.');

  context.subscriptions.push({
    dispose: () => serverProcess.kill()
  });
```

## DELIVERABLES
- Standalone Python proxy script (`pii_proxy.py`) with streaming rehydration.
- VS Code / Antigravity wrapper extension (`extension.ts` + `package.json`).
- Packaging script generating a one-click installable `.vsix`.
