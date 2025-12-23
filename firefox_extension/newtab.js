(() => {
  const CONFIG_URL = browser.runtime.getURL("config.json");

  function getHint() {
    return document.getElementById("hint");
  }

  function getSearchElements() {
    return {
      form: document.getElementById("search-form"),
      input: document.getElementById("search-input"),
    };
  }

  async function loadConfig() {
    try {
      const resp = await fetch(CONFIG_URL, { cache: "no-store" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      return null;
    }
  }

  function resolveImageUrl(config) {
    const base = browser.runtime.getURL("randombg_wallpaper.png");
    const stamp = config && config.updated ? config.updated : Date.now();
    return `${base}?t=${stamp}`;
  }

  function setBackground(url) {
    const img = new Image();
    img.onload = () => {
      document.documentElement.style.backgroundImage = `url("${url}")`;
      document.body.style.backgroundImage = `url("${url}")`;
      const hint = getHint();
      if (hint) {
        hint.textContent = "";
        hint.style.display = "none";
      }
    };
    img.onerror = () => {
      const hint = getHint();
      if (hint) {
        hint.textContent = [
          "Konnte Hintergrund nicht laden.",
          `Versuchter Pfad: ${url}`,
          "Bitte RandomBG ausfuehren, damit das Bild in die Extension kopiert wird.",
        ].join("\n");
        hint.style.display = "block";
      }
    };
    img.src = url;
  }

  function isProbablyUrl(value) {
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) return true;
    if (value.includes(" ")) return false;
    return value.includes(".");
  }

  function handleSearch() {
    const { form, input } = getSearchElements();
    if (!form || !input) return;

    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const raw = (input.value || "").trim();
      if (!raw) {
        input.focus();
        return;
      }
      let target = raw;
      if (isProbablyUrl(raw)) {
        if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) {
          target = "https://" + raw;
        }
      } else {
        target = "https://www.google.com/search?q=" + encodeURIComponent(raw);
      }
      window.location.href = target;
    });

    input.focus({ preventScroll: true });
  }

  (async () => {
    const config = await loadConfig();
    const url = resolveImageUrl(config);
    setBackground(url);
    handleSearch();
  })();
})();
