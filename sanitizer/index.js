import { Sanitizer } from "./sanitize.js";
const sanitizeButton = document.getElementById("sanitize");
const htmlInput = document.getElementById("input");
const htmlOutput = document.getElementById("output");
const htmlRender = document.getElementById("rendered");
const analyzeButton = document.getElementById("analyze-intent");
const intentResult = document.getElementById("intent-result");

sanitizeButton.addEventListener("click", function () {
  const html = htmlInput.value;
  const cleaned = Sanitizer.sanitize(html);
  htmlOutput.value = cleaned;
  htmlRender.setAttribute("srcdoc", cleaned);
});

analyzeButton.addEventListener("click", async function () {
  analyzeButton.disabled = true;
  intentResult.textContent = "Analyzing input...";

  try {
    const response = await fetch("http://127.0.0.1:8000/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: htmlInput.value }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || `Request failed (${response.status})`);
    }

    const labels = {
      benign: "Benign",
      potentially_malicious: "Potentially malicious",
    };
    const label = labels[result.label];
    if (!label) {
      throw new Error("Classifier returned an unknown label");
    }
    intentResult.textContent = `Model assessment: ${label} (${(
      result.confidence * 100
    ).toFixed(1)}% confidence). Advisory only; sanitizer behavior is unchanged.`;
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown analysis error";
    intentResult.textContent = `Intent analysis unavailable: ${message}`;
  } finally {
    analyzeButton.disabled = false;
  }
});
