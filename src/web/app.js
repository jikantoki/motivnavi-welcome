/* Motivnavi OSへようこそ — app.js */
(() => {
  "use strict";

  const info = window.MOTIVNAVI || { native: false, version: "" };
  const bridge =
    window.webkit &&
    window.webkit.messageHandlers &&
    window.webkit.messageHandlers.motivnavi;

  const views = new Map(
    [...document.querySelectorAll(".view")].map((el) => [el.dataset.view, el])
  );
  const toastEl = document.querySelector(".toast");
  const lightbox = document.querySelector(".lightbox");
  const lightboxImg = lightbox.querySelector("img");

  /* ---------- 画面サイズ（vw/vh の代わり） ----------
     WebKitGTK は拡大率(ズーム)を変えると vw/vh の計算がずれるため、
     実際の表示サイズから 1% の長さを CSS 変数 --vw / --vh に入れて使う。 */
  function updateViewportUnits() {
    const root = document.documentElement.style;
    root.setProperty("--vw", window.innerWidth / 100 + "px");
    root.setProperty("--vh", window.innerHeight / 100 + "px");
  }
  updateViewportUnits();
  window.addEventListener("resize", updateViewportUnits);

  /* ---------- 画面切り替え ---------- */
  function show(name) {
    if (!views.has(name)) name = "home";
    views.forEach((el, key) => {
      const active = key === name;
      el.classList.toggle("is-active", active);
      if (active) el.scrollTop = 0;
    });
    closeLightbox();
  }

  function route() {
    show(location.hash.replace(/^#/, "") || "home");
  }

  function goHome() {
    history.replaceState(null, "", location.pathname);
    route();
  }

  window.addEventListener("hashchange", route);

  /* ---------- 通知 ---------- */
  let toastTimer = 0;
  function toast(message, kind) {
    toastEl.textContent = message;
    toastEl.classList.remove("is-error", "is-warn");
    if (kind === "error") toastEl.classList.add("is-error");
    if (kind === "warn") toastEl.classList.add("is-warn");
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 3600);
  }

  /* ---------- アプリ起動（Python へ依頼） ---------- */
  let requestId = 0;
  const pending = new Map();

  function launch(button) {
    const action = button.dataset.launch;
    if (!bridge) {
      toast("プレビュー表示中のため、アプリは起動できません", "warn");
      return;
    }
    const id = ++requestId;
    pending.set(id, button);
    button.classList.add("is-launching");
    bridge.postMessage(JSON.stringify({ type: "launch", action, id }));
  }

  window.motivnavi = {
    onResult(result) {
      const button = pending.get(result.id);
      pending.delete(result.id);
      toast(result.message, result.ok ? "ok" : "error");
      if (button) {
        setTimeout(
          () => button.classList.remove("is-launching"),
          result.ok ? 2500 : 0
        );
      }
    },
  };

  /* ---------- 写真の拡大 ---------- */
  function openLightbox(img) {
    lightboxImg.src = img.src;
    lightboxImg.alt = img.alt;
    lightbox.hidden = false;
  }
  function closeLightbox() {
    lightbox.hidden = true;
  }
  lightbox.addEventListener("click", closeLightbox);

  /* ---------- タップ ---------- */
  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-open], [data-launch], [data-back], [data-zoom]");
    if (!target) return;

    if (target.hasAttribute("data-back")) return goHome();
    if (target.hasAttribute("data-zoom")) return openLightbox(target);
    if (target.dataset.open) {
      location.hash = target.dataset.open;
      return;
    }
    if (target.dataset.launch) launch(target);
  });

  // 押した感触（タッチでも :active が効かない環境向け）
  document.addEventListener("pointerdown", (e) => {
    const tile = e.target.closest(".tile");
    if (!tile) return;
    tile.classList.add("is-pressed");
    const release = () => tile.classList.remove("is-pressed");
    window.addEventListener("pointerup", release, { once: true });
    window.addEventListener("pointercancel", release, { once: true });
  });

  /* ---------- キーボード ---------- */
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" && e.key !== "Backspace") return;
    if (!lightbox.hidden) return closeLightbox();
    if (location.hash) goHome();
  });

  document.addEventListener("contextmenu", (e) => e.preventDefault());

  /* ---------- 初期表示 ---------- */
  const versionEl = document.querySelector(".version");
  if (versionEl && info.version) versionEl.textContent = "Welcome app v" + info.version;

  goHome();
})();
