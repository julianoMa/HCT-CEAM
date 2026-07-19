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

  // ── Modal de confirmation (suppression et archivage) ──
  const confirmModal = document.querySelector("#confirm-modal");
  const confirmTitle = document.querySelector("#confirm-modal-title");
  const confirmText = document.querySelector("#confirm-modal-text");
  const confirmBtn = document.querySelector("#confirm-modal-confirm");
  const cancelBtn = document.querySelector("#confirm-modal-cancel");
  let formToSubmit = null;

  function closeConfirmModal() {
    confirmModal?.classList.remove("is-visible");
    confirmModal?.setAttribute("aria-hidden", "true");
    formToSubmit = null;
  }

  function openConfirmModal(options) {
    formToSubmit = options.form;
    if (confirmTitle) confirmTitle.textContent = options.title;
    if (confirmText) confirmText.textContent = options.text;
    if (confirmBtn) {
      confirmBtn.textContent = options.confirmLabel;
      confirmBtn.classList.toggle("btn-danger", options.danger);
      confirmBtn.classList.toggle("btn-primary", !options.danger);
    }
    confirmModal?.classList.add("is-visible");
    confirmModal?.setAttribute("aria-hidden", "false");
  }

  document.querySelectorAll("[data-confirm-delete]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const reference = btn.dataset.reference || "ce dossier";
      openConfirmModal({
        form: btn.closest("form[data-delete-form]"),
        title: "Confirmer la suppression",
        text:
          `Cette action est irréversible : le dossier ${reference} et toutes ses ` +
          "données (réponses, historique, preuves) seront définitivement supprimés. Continuer ?",
        confirmLabel: "Supprimer définitivement",
        danger: true,
      });
    });
  });

  document.querySelectorAll("[data-confirm-archive]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const reference = btn.dataset.reference || "ce dossier";
      openConfirmModal({
        form: btn.closest("form[data-archive-form]"),
        title: "Confirmer l'archivage",
        text:
          `Le dossier ${reference} ne sera plus visible par le déclarant et n'apparaîtra ` +
          "plus que dans Archives. Continuer ?",
        confirmLabel: "Archiver le dossier",
        danger: false,
      });
    });
  });

  document.querySelectorAll("[data-confirm-non-recevable]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const reference = btn.dataset.reference || "ce dossier";
      openConfirmModal({
        form: btn.closest("form[data-non-recevable-form]"),
        title: "Marquer le dossier comme non recevable ?",
        text:
          `Le dossier ${reference} sera orienté vers une clôture sans instruction complète ` +
          '(classement "Sans objet" proposé par défaut). Continuer ?',
        confirmLabel: "Confirmer",
        danger: false,
      });
    });
  });

  document.querySelectorAll("[data-confirm-cloture]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const reference = btn.dataset.reference || "ce dossier";
      openConfirmModal({
        form: btn.closest("form[data-cloture-form]"),
        title: "Clôturer définitivement ce dossier ?",
        text:
          `Cette action verrouillera tous les échanges du dossier ${reference} et le passera ` +
          "en lecture seule. Cette action est définitive. Continuer ?",
        confirmLabel: "Clôturer le dossier",
        danger: true,
      });
    });
  });

  // Le bouton "Clôturer le dossier" reste désactivé tant qu'aucun
  // classement n'est sélectionné (le rendu serveur ne gère que l'état
  // initial ; ceci couvre un changement de sélection sans rechargement).
  const clotureSelect = document.getElementById("cloture-classement-select");
  const clotureSubmitBtn = document.getElementById("cloture-submit-btn");
  if (clotureSelect && clotureSubmitBtn) {
    const syncClotureButton = () => {
      clotureSubmitBtn.disabled = !clotureSelect.value;
    };
    clotureSelect.addEventListener("change", syncClotureButton);
    syncClotureButton(); // état correct dès le chargement, pas seulement après un changement
  }

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

  // ── Compression d'images avant envoi ──
  // Les pièces jointes sont stockées dans Firestore (limite : 1 Mo par
  // document, donc 650 Ko max par fichier une fois encodé). Une photo de
  // téléphone dépasse très souvent ça en brut : on la redimensionne et on
  // la réencode en JPEG côté navigateur avant l'envoi, pour que l'immense
  // majorité des photos passent sans que la personne ait à s'en soucier.
  // Les PDF et les GIF (animation) ne sont jamais touchés.
  const MAX_IMAGE_DIMENSION = 1600;
  const TARGET_MAX_BYTES = 650 * 1024;

  function compressImageFile(file) {
    return new Promise((resolve) => {
      if (!file.type.startsWith("image/") || file.type === "image/gif") {
        resolve(file);
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          let { width, height } = img;
          if (width > MAX_IMAGE_DIMENSION || height > MAX_IMAGE_DIMENSION) {
            const scale = MAX_IMAGE_DIMENSION / Math.max(width, height);
            width = Math.round(width * scale);
            height = Math.round(height * scale);
          }
          const canvas = document.createElement("canvas");
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0, width, height);

          const tryQuality = (quality) => {
            canvas.toBlob(
              (blob) => {
                if (!blob) {
                  resolve(file);
                  return;
                }
                if (blob.size > TARGET_MAX_BYTES && quality > 0.35) {
                  tryQuality(quality - 0.15);
                  return;
                }
                const newName = file.name.replace(/\.(png|gif|webp|jpe?g)$/i, "") + ".jpg";
                const compressed = new File([blob], newName, { type: "image/jpeg" });
                resolve(compressed.size < file.size ? compressed : file);
              },
              "image/jpeg",
              quality
            );
          };
          tryQuality(0.75);
        };
        img.onerror = () => resolve(file);
        img.src = event.target.result;
      };
      reader.onerror = () => resolve(file);
      reader.readAsDataURL(file);
    });
  }

  async function compressFileInput(input) {
    const files = Array.from(input.files || []);
    if (files.length === 0) return;
    const compressed = await Promise.all(files.map(compressImageFile));
    const dataTransfer = new DataTransfer();
    compressed.forEach((f) => dataTransfer.items.add(f));
    input.files = dataTransfer.files;
  }

  document.querySelectorAll("[data-compress-images]").forEach((input) => {
    input.addEventListener("change", async () => {
      input.disabled = true;
      await compressFileInput(input);
      input.disabled = false;
      renderPendingAttachments(input);
    });
  });

  // ── Aperçu (en cards) des fichiers joints dans le composer du chat,
  // avant l'envoi du message — même look que les cards de pièces jointes
  // déjà envoyées (preuves, réponses), avec un bouton pour retirer un
  // fichier avant de cliquer sur Envoyer. ──
  function fileIconSvg(isPdf) {
    return isPdf
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>';
  }

  function renderPendingAttachments(input) {
    const composer = input.closest("form");
    const container = composer?.querySelector("[data-pending-attachments]");
    if (!container) return;

    container.innerHTML = "";
    Array.from(input.files || []).forEach((file, index) => {
      const isPdf = file.type === "application/pdf";
      const sizeKo = Math.ceil(file.size / 1024);

      const card = document.createElement("div");
      card.className = "attachment-card attachment-card--pending";
      card.innerHTML = `
        <div class="attachment-card__icon">${fileIconSvg(isPdf)}</div>
        <div class="attachment-card__info">
          <span class="attachment-card__name">${file.name}</span>
          <span class="attachment-card__meta">${isPdf ? "PDF" : "Image"} · ${sizeKo} Ko</span>
        </div>
        <button type="button" class="attachment-card__remove" aria-label="Retirer ce fichier" data-remove-index="${index}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll("[data-remove-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const removeIndex = Number(btn.dataset.removeIndex);
        const dataTransfer = new DataTransfer();
        Array.from(input.files).forEach((file, i) => {
          if (i !== removeIndex) dataTransfer.items.add(file);
        });
        input.files = dataTransfer.files;
        renderPendingAttachments(input);
      });
    });
  }

  document.querySelectorAll(".chat-panel__attach-input").forEach((input) => {
    input.addEventListener("change", () => {
      // Si la compression d'images est aussi active sur ce champ, son
      // propre gestionnaire (ci-dessus) rafraîchit déjà l'aperçu une fois
      // les fichiers compressés — pas besoin de le refaire ici pour ce cas.
      if (!input.hasAttribute("data-compress-images")) {
        renderPendingAttachments(input);
      }
    });
    // Après un envoi réussi la page se recharge entièrement (redirection),
    // donc pas besoin de vider l'aperçu manuellement après soumission.
  });

  // ── Prévisualisation des pièces jointes (image ou PDF) dans un modal ──
  // Un seul modal partagé par page : son contenu est injecté dynamiquement
  // selon la pièce jointe cliquée, plutôt que d'avoir un modal par fichier.
  const previewModal = document.getElementById("attachment-preview-modal");
  if (previewModal) {
    const previewBody = previewModal.querySelector("[data-preview-body]");
    const previewTitle = previewModal.querySelector("[data-preview-title]");
    const previewDownload = previewModal.querySelector("[data-preview-download]");

    document.querySelectorAll("[data-preview-url]").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const url = trigger.dataset.previewUrl;
        const type = trigger.dataset.previewType;
        const name = trigger.dataset.previewName;

        if (previewTitle) previewTitle.textContent = name;
        if (previewDownload) {
          const separator = url.includes("?") ? "&" : "?";
          previewDownload.href = `${url}${separator}download=1`;
        }

        previewBody.innerHTML = "";
        if (type === "image") {
          const img = document.createElement("img");
          img.src = url;
          img.alt = name;
          img.className = "attachment-preview__image";
          previewBody.appendChild(img);
        } else if (type === "pdf") {
          const iframe = document.createElement("iframe");
          iframe.src = url;
          iframe.className = "attachment-preview__pdf";
          previewBody.appendChild(iframe);
        } else {
          const p = document.createElement("p");
          p.className = "empty-state__text";
          p.textContent = "Aperçu non disponible pour ce type de fichier — utilise le téléchargement.";
          previewBody.appendChild(p);
        }

        previewModal.classList.add("is-visible");
      });
    });
  }

  // ── Protection anti double-clic sur les formulaires ──
  // Désactive le(s) bouton(s) de soumission juste après le premier clic,
  // pour éviter qu'un double-clic (ou un clic impatient pendant le
  // chargement) n'envoie deux fois le même formulaire — dépôt de rapport,
  // réponse, suivi interne, ajout de tiers, etc. Un formulaire peut passer
  // outre avec l'attribut data-allow-resubmit si jamais nécessaire.
  document.querySelectorAll('form[method="post" i]').forEach((form) => {
    if (form.hasAttribute("data-allow-resubmit")) return;
    form.addEventListener("submit", () => {
      if (form.dataset.submitted === "true") return;
      form.dataset.submitted = "true";
      const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
      submitButtons.forEach((btn) => {
        // Laisser le clic initial partir avant de désactiver, sinon
        // certains navigateurs annulent la valeur du bouton cliqué.
        setTimeout(() => {
          btn.disabled = true;
          btn.classList.add("is-submitting");
        }, 0);
      });
    });
  });

  // ── Onglets de la page de détail (Rapport / Échanges / Instruction CEAM) ──
  const tabTriggers = document.querySelectorAll("[data-tab-trigger]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");
  if (tabTriggers.length && tabPanels.length) {
    const activateTab = (name) => {
      let matched = false;
      tabPanels.forEach((panel) => {
        const isMatch = panel.dataset.tabPanel === name;
        panel.classList.toggle("is-active", isMatch);
        if (isMatch) matched = true;
      });
      // Si l'onglet demandé n'existe pas (ex: lien vers #instruction pour
      // quelqu'un qui n'a pas accès à cet onglet), on retombe sur "rapport".
      if (!matched) {
        tabPanels.forEach((panel) => panel.classList.toggle("is-active", panel.dataset.tabPanel === "rapport"));
        name = "rapport";
      }
      tabTriggers.forEach((btn) => {
        btn.classList.toggle("is-active", btn.dataset.tabTrigger === name);
      });
      if (name === "echanges") {
        const chatArea = document.querySelector("[data-chat-scroll]");
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
      }
    };

    tabTriggers.forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.tabTrigger;
        history.replaceState(null, "", `#${name}`);
        activateTab(name);
      });
    });

    const initialTab = (window.location.hash || "").replace("#", "") || "rapport";
    activateTab(initialTab);
  }
})();