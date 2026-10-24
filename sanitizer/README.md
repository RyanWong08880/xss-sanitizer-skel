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
