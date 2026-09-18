import { Sanitizer } from "./sanitize.js";
const sanitizeButton = document.getElementById("sanitize");
const htmlInput = document.getElementById("input");
const htmlOutput = document.getElementById("output");
const htmlRender = document.getElementById("rendered");

sanitizeButton.addEventListener("click", function () {
  const html = htmlInput.value;
  const cleaned = Sanitizer.sanitize(html);
  htmlOutput.value = cleaned;
  htmlRender.setAttribute("srcdoc", cleaned);
});
