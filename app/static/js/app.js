(function () {
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  const toggle = document.querySelector("[data-sidebar-toggle]");

  function closeSidebar() {
    sidebar?.classList.remove("is-open");
    overlay?.classList.remove("is-visible");
    document.body.classList.remove("sidebar-open");
  }

  toggle?.addEventListener("click", () => {
    const open = sidebar?.classList.toggle("is-open");
    overlay?.classList.toggle("is-visible", open);
    document.body.classList.toggle("sidebar-open", open);
  });

  overlay?.addEventListener("click", closeSidebar);

  document.querySelectorAll(".flash[data-auto-dismiss]").forEach((el) => {
    setTimeout(() => {
      el.classList.add("is-hiding");
      setTimeout(() => el.remove(), 300);
    }, 5000);
  });

  document.querySelectorAll(".flash__close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const flash = btn.closest(".flash");
      flash?.classList.add("is-hiding");
      setTimeout(() => flash?.remove(), 300);
    });
  });

  // ── Modal de confirmation (suppression définitive) ──
  const confirmModal = document.querySelector("#confirm-modal");
  const confirmText = document.querySelector("#confirm-modal-text");
  const confirmBtn = document.querySelector("#confirm-modal-confirm");
  const cancelBtn = document.querySelector("#confirm-modal-cancel");
  let formToSubmit = null;

  function closeConfirmModal() {
    confirmModal?.classList.remove("is-visible");
    confirmModal?.setAttribute("aria-hidden", "true");
    formToSubmit = null;
  }

  document.querySelectorAll("[data-confirm-delete]").forEach((btn) => {
    btn.addEventListener("click", () => {
      formToSubmit = btn.closest("form[data-delete-form]");
      const reference = btn.dataset.reference || "ce dossier";
      if (confirmText) {
        confirmText.textContent =
          `Cette action est irréversible : le dossier ${reference} et toutes ses ` +
          "données (réponses, historique, preuves) seront définitivement supprimés. Continuer ?";
      }
      confirmModal?.classList.add("is-visible");
      confirmModal?.setAttribute("aria-hidden", "false");
    });
  });

  cancelBtn?.addEventListener("click", closeConfirmModal);

  confirmModal?.addEventListener("click", (event) => {
    if (event.target === confirmModal) closeConfirmModal();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeConfirmModal();
    document.querySelectorAll(".modal-overlay.is-visible").forEach((overlay) => {
      overlay.classList.remove("is-visible");
      overlay.setAttribute("aria-hidden", "true");
    });
  });

  confirmBtn?.addEventListener("click", () => {
    if (formToSubmit) {
      formToSubmit.submit();
    }
    closeConfirmModal();
  });

  // ── Modals génériques (ex: "Envoyer une réponse") ──
  document.querySelectorAll("[data-open-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = document.getElementById(btn.dataset.openModal);
      modal?.classList.add("is-visible");
      modal?.setAttribute("aria-hidden", "false");
    });
  });

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-overlay");
      modal?.classList.remove("is-visible");
      modal?.setAttribute("aria-hidden", "true");
    });
  });

  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        overlay.classList.remove("is-visible");
        overlay.setAttribute("aria-hidden", "true");
      }
    });
  });

  // ── Bascule générique d'affichage (ex: bouton "Modifier" du règlement) ──
  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.toggle);
      target?.classList.toggle("is-hidden");
    });
  });

  // ── Thème clair / sombre ──
  const themeToggle = document.querySelector("#theme-toggle");
  const themeEmoji = document.querySelector("#theme-toggle-emoji");

  function updateThemeIcon() {
    if (!themeEmoji) return;
    const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    themeEmoji.textContent = current === "dark" ? "☀️" : "🌙";
  }

  updateThemeIcon();

  themeToggle?.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("ceam-theme", next);
    updateThemeIcon();
  });
})();