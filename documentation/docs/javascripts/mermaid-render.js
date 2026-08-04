void (async () => {
  const mermaidRuntime = globalThis.mermaid;

  if (!mermaidRuntime) {
    throw new Error("The locally pinned Mermaid runtime was not loaded.");
  }

  mermaidRuntime.initialize({
    startOnLoad: false,
    securityLevel: "strict",
  });

  for (const [index, source] of document
    .querySelectorAll("pre.mermaid-source")
    .entries()) {
    const diagramId = `lms-mermaid-${index}`;
    const container = document.createElement("figure");
    container.className = "mermaid-diagram";
    container.setAttribute("aria-label", "Diagrama de documentación");

    const { svg, bindFunctions } = await mermaidRuntime.render(
      diagramId,
      source.textContent,
    );
    container.innerHTML = svg;
    source.replaceWith(container);
    bindFunctions?.(container);
  }
})();
