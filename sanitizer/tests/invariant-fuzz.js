import { Sanitizer } from "../sanitize.js";

const ALLOWED_TAGS = new Set([
  "a",
  "abbr",
  "b",
  "blockquote",
  "br",
  "caption",
  "code",
  "del",
  "div",
  "em",
  "figcaption",
  "figure",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "i",
  "img",
  "ins",
  "kbd",
  "li",
  "ol",
  "p",
  "pre",
  "q",
  "s",
  "small",
  "span",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "tfoot",
  "th",
  "thead",
  "time",
  "tr",
  "u",
  "ul",
]);

const GLOBAL_ATTRIBUTES = new Set(["class", "dir", "hidden", "id", "lang", "title"]);
const TAG_ATTRIBUTES = {
  a: new Set(["href", "hreflang", "rel", "target"]),
  blockquote: new Set(["cite"]),
  del: new Set(["cite", "datetime"]),
  img: new Set(["alt", "height", "loading", "src", "width"]),
  ins: new Set(["cite", "datetime"]),
  li: new Set(["value"]),
  ol: new Set(["reversed", "start", "type"]),
  q: new Set(["cite"]),
  td: new Set(["colspan", "headers", "rowspan"]),
  th: new Set(["colspan", "headers", "rowspan", "scope"]),
  time: new Set(["datetime"]),
};
const SAFE_TAGS = ["p", "span", "strong", "em", "div", "blockquote"];
const SAFE_TEXT = ["alpha", "plain text", "marker-123", "sample &amp; text"];
const INERT_ATTRIBUTE_VARIANTS = [
  ' title="marker"',
  ' data-marker="inert"',
  ' class="sample"',
  ' onclick="inert-marker"',
  ' onerror="inert-marker"',
  ' style="color: blue"',
];
const INERT_UNSAFE_URLS = ["javascript:", "data:", "vbscript:"];
const MAX_CASES = 600;

function generateCases() {
  const cases = new Set([
    "<p>plain text</p>",
    '<a href="https://example.test/path" title="sample">link</a>',
    '<img src="https://example.test/image.png" alt="sample">',
    "<section>safe <strong>nested</strong> text</section>",
  ]);

  for (const tag of SAFE_TAGS) {
    for (const text of SAFE_TEXT) {
      cases.add(`<${tag}>${text}</${tag}>`);
      cases.add(`<${tag} title="marker">${text}</${tag}>`);
    }

    for (const attribute of INERT_ATTRIBUTE_VARIANTS) {
      cases.add(`<${tag}${attribute}>marker</${tag}>`);
    }
  }

  for (const scheme of INERT_UNSAFE_URLS) {
    cases.add(`<a href="${scheme}">inert link marker</a>`);
    cases.add(`<img src="${scheme}" alt="inert image marker">`);
  }

  const safePairs = [
    ["p", "strong"],
    ["div", "em"],
    ["blockquote", "span"],
  ];
  for (const [outer, inner] of safePairs) {
    for (const text of SAFE_TEXT) {
      cases.add(`<${outer}><${inner}>${text}</${inner}></${outer}>`);
    }
  }

  return [...cases].slice(0, MAX_CASES);
}

function inspectOutput(html) {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const violations = [];
  const elements = [...parsed.body.querySelectorAll("*")];

  for (const element of elements) {
    const tagName = element.tagName.toLowerCase();
    if (!ALLOWED_TAGS.has(tagName)) {
      violations.push(`disallowed tag <${tagName}>`);
    }

    for (const attribute of [...element.attributes]) {
      const name = attribute.name.toLowerCase();
      if (name.startsWith("on")) {
        violations.push(`event-handler attribute ${name}`);
      } else if (
        !GLOBAL_ATTRIBUTES.has(name) &&
        !TAG_ATTRIBUTES[tagName]?.has(name)
      ) {
        violations.push(`disallowed attribute ${name} on <${tagName}>`);
      }

      if (name === "href" || name === "src") {
        let url;
        try {
          url = new URL(attribute.value, document.baseURI);
        } catch {
          violations.push(`invalid ${name} URL`);
          continue;
        }

        const allowedProtocols =
          name === "href" ? ["http:", "https:", "mailto:"] : ["http:", "https:"];
        if (!allowedProtocols.includes(url.protocol)) {
          violations.push(`unsafe ${name} protocol ${url.protocol}`);
        }
      }
    }
  }

  return violations;
}

function runChecks() {
  const cases = generateCases();
  const results = cases.map((input, index) => {
    const output = Sanitizer.sanitize(input);
    const violations = inspectOutput(output);
    return {
      index: index + 1,
      input,
      output,
      violations,
    };
  });
  const failures = results.filter((result) => result.violations.length > 0);
  return { results, failures };
}

function renderResults({ results, failures }) {
  const summary = document.getElementById("summary");
  const resultsList = document.getElementById("results");
  resultsList.replaceChildren();
  summary.textContent = `${results.length} deterministic cases checked; ${failures.length} invariant failures.`;

  for (const result of results) {
    const item = document.createElement("li");
    item.textContent =
      result.violations.length === 0
        ? `Case ${result.index}: passed`
        : `Case ${result.index}: ${result.violations.join(", ")}; input: ${result.input}`;
    item.dataset.status = result.violations.length === 0 ? "passed" : "failed";
    resultsList.append(item);
  }
}

document.getElementById("run").addEventListener("click", () => {
  const report = runChecks();
  renderResults(report);
  window.dispatchEvent(
    new CustomEvent("sanitizer-invariant-results", { detail: report })
  );
});
