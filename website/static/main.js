const reveals = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("shown");
        observer.unobserve(entry.target);
      }
    }
  }, { rootMargin: "0px 0px -8% 0px" });
  reveals.forEach((element) => observer.observe(element));
} else {
  reveals.forEach((element) => element.classList.add("shown"));
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = "Copied";
      button.classList.add("done");
    } catch {
      button.textContent = "Press ⌘C";
      const range = document.createRange();
      range.selectNodeContents(button.previousElementSibling);
      getSelection().removeAllRanges();
      getSelection().addRange(range);
    }
    setTimeout(() => {
      button.textContent = "Copy";
      button.classList.remove("done");
    }, 2000);
  });
});

// Each group of tab buttons shows one panel and hides the others it controls.
document.querySelectorAll("[data-tabs]").forEach((group) => {
  const buttons = group.querySelectorAll("[data-tab]");
  const show = (id) => buttons.forEach((button) => {
    const on = button.dataset.tab === id;
    button.setAttribute("aria-pressed", String(on));
    document.getElementById(button.dataset.tab).classList.toggle("active", on);
  });
  buttons.forEach((button) => button.addEventListener("click", () => show(button.dataset.tab)));
});

// A code block that scrolls sideways takes keyboard focus, so it can be scrolled without a mouse; one that fits does not.
if ("ResizeObserver" in window) {
  const scrollers = new ResizeObserver((entries) => {
    for (const { target } of entries) {
      if (target.scrollWidth > target.clientWidth) target.tabIndex = 0;
      else target.removeAttribute("tabindex");
    }
  });
  document.querySelectorAll(".code pre").forEach((pre) => scrollers.observe(pre));
}
