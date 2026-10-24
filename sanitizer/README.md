# XSS Sanitizer
This is a simple website to provide an interactive frontend to test your XSS sanitizer.

## Running
Serve the repository root with a static file server, for example:

```sh
python3 -m http.server 8080
```

Open http://localhost:8080/sanitizer/. The sanitizer works without the model API. To use **Analyze intent**, start the optional local API and train its model as described in [intent/README.md](./intent/README.md). Do not expose the local API to the public internet.

## Developing
Edit the sanitizer at `sanitize.js`. The `Sanitizer.sanitize()` function takes in HTML as a string, and returns sanitized HTML as a string.

## Local invariant checks
Open http://localhost:8080/sanitizer/tests/invariant-fuzz.html while serving the
repository root, then select **Run checks**. The bounded, deterministic harness
varies inert markup and marker attributes locally and checks sanitized output
for disallowed tags, attributes, event handlers, and unsafe URL protocols. It
does not use a model, generate executable payloads, contact a service, or
modify the sanitizer. A failed check is a regression signal to investigate,
not an automatic sanitizer change.
