const GLOBAL_ATTRIBUTES = new Set(["class", "dir", "hidden", "id", "lang", "title"]);

const ALLOWED_ATTRIBUTES = {
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

const ALLOWED_TAGS = new Set([
  "a",
  "abbr",
  "b",
  "blockquote",
  "br",
  "caption",
  "code",
  "ins",
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

const DROP_CONTENT_TAGS = new Set(["script", "style", "template"]);

function isSafeUrl(value, allowMailto = false) {
  try {
    const url = new URL(value, document.baseURI);
    const allowedProtocols = allowMailto
      ? ["http:", "https:", "mailto:"]
      : ["http:", "https:"];
    return allowedProtocols.includes(url.protocol);
  } catch {
    return false;
  }
}

function sanitizeElement(element) {
  for (const attribute of [...element.attributes]) {
    const name = attribute.name.toLowerCase();
    const allowed =
      GLOBAL_ATTRIBUTES.has(name) ||
      ALLOWED_ATTRIBUTES[element.tagName.toLowerCase()]?.has(name);

    if (!allowed) {
      element.removeAttribute(attribute.name);
      continue;
    }

    if (name === "href" && !isSafeUrl(attribute.value, true)) {
      element.removeAttribute(attribute.name);
    }
    if (name === "src" && !isSafeUrl(attribute.value)) {
      element.removeAttribute(attribute.name);
    }
  }

  for (const child of [...element.children]) {
    sanitizeNode(child);
  }
}

function sanitizeNode(node) {
  const tagName = node.tagName.toLowerCase();

  if (DROP_CONTENT_TAGS.has(tagName)) {
    node.remove();
    return;
  }

  if (!ALLOWED_TAGS.has(tagName)) {
    const parent = node.parentNode;
    while (node.firstChild) {
      const child = node.firstChild;
      parent.insertBefore(child, node);
      if (child.nodeType === Node.ELEMENT_NODE) {
        sanitizeNode(child);
      }
    }
    node.remove();
    return;
  }

  sanitizeElement(node);
}

export class Sanitizer {
  static sanitize(input) {
    const parser = new DOMParser();
    const parsedDocument = parser.parseFromString(
      `<body>${String(input)}</body>`,
      "text/html"
    );

    for (const child of [...parsedDocument.body.children]) {
      sanitizeNode(child);
    }

    return parsedDocument.body.innerHTML;
  }
}
