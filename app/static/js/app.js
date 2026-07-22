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
    // 1. Cherche d'abord un conteneur ciblé explicitement par data-pending-container
    // 2. Sinon, fallback sur l'ancien comportement (dans le formulaire le plus proche)
    const containerId = input.getAttribute("data-pending-container");
    const container = containerId 
      ? document.getElementById(containerId) 
      : input.closest("form")?.querySelector("[data-pending-attachments]");
      
    if (!container) return;

    container.innerHTML = "";
    Array.from(input.files || []).forEach((file, index) => {
      const isPdf = file.type === "application/pdf";
      const sizeKo = Math.ceil(file.size / 1024);

      const card = document.createElement("div");
      card.className = "attachment-card attachment-card--pending";
      card.innerHTML = `
        <div class="attachment-card__icon">
          ${fileIconSvg(isPdf)}
        </div>
        <div class="attachment-card__info">
          <span class="attachment-card__name">${file.name}</span>
          <span class="attachment-card__meta">${isPdf ? "PDF" : "Image"} · ${sizeKo} Ko</span>
        </div>
        <button type="button" class="attachment-card__remove" data-remove-index="${index}" title="Retirer le fichier">×</button>
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
  });

  // ── Glisser-déposer de fichiers dans le chat ──
  // Déposer un fichier n'envoie pas le message directement, il se
  // contente de le joindre (comme cliquer sur "Joindre") : la personne
  // doit toujours valider l'envoi ensuite (bouton ou Ctrl+Entrée).
  document.querySelectorAll(".chat-panel").forEach((chatPanel) => {
    let dragCounter = 0;

    chatPanel.addEventListener("dragenter", (event) => {
      event.preventDefault();
      dragCounter += 1;
      chatPanel.classList.add("is-drag-over");
    });

    chatPanel.addEventListener("dragover", (event) => {
      // Nécessaire pour autoriser le "drop" — sans ça, le navigateur
      // refuse la dépose et ouvre le fichier dans un nouvel onglet.
      event.preventDefault();
    });

    chatPanel.addEventListener("dragleave", () => {
      dragCounter = Math.max(0, dragCounter - 1);
      if (dragCounter === 0) chatPanel.classList.remove("is-drag-over");
    });

    chatPanel.addEventListener("drop", (event) => {
      event.preventDefault();
      dragCounter = 0;
      chatPanel.classList.remove("is-drag-over");

      const droppedFiles = event.dataTransfer?.files;
      if (!droppedFiles || droppedFiles.length === 0) return;

      // Les fichiers sont joints à la conversation ACTIVE (celle
      // affichée à l'écran), pas à une conversation masquée.
      const activeInput = chatPanel.querySelector(".chat-conversation-panel.is-active .chat-panel__attach-input");
      if (!activeInput) return;

      const dataTransfer = new DataTransfer();
      Array.from(activeInput.files || []).forEach((f) => dataTransfer.items.add(f));
      Array.from(droppedFiles).forEach((f) => dataTransfer.items.add(f));
      activeInput.files = dataTransfer.files;
      // Déclenche le même traitement que si les fichiers avaient été
      // choisis via le bouton "Joindre" (compression + aperçu inclus).
      activeInput.dispatchEvent(new Event("change"));
    });
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
          if (!btn.querySelector(".btn-inline-spinner")) {
            const spinner = document.createElement("span");
            spinner.className = "btn-inline-spinner";
            spinner.setAttribute("aria-hidden", "true");
            btn.prepend(spinner);
          }
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
        const chatArea = document.querySelector(".chat-conversation-panel.is-active [data-chat-scroll]");
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

  // ── Brouillon du formulaire de dépôt (localStorage) ──
  // Les fichiers de preuve ne sont volontairement pas sauvegardés (un
  // navigateur ne permet pas de sérialiser un File dans localStorage) —
  // seuls les champs texte le sont. La case de certification n'est pas
  // non plus restaurée automatiquement : c'est un engagement conscient,
  // à recocher à chaque fois.
  const depotForm = document.getElementById("depot-form");
  if (depotForm) {
    const DRAFT_KEY = "ceam-depot-draft";
    const DRAFT_FIELDS = [
      "plaignant_last_name", "plaignant_first_name", "plaignant_rank", "plaignant_affectation",
      "concerne_last_name", "concerne_first_name", "concerne_rank", "concerne_affectation",
      "event_date", "event_hour", "location", "witness", "description", "proof",
    ];
    // Champs utilisés uniquement pour détecter "le formulaire a-t-il déjà
    // du contenu réel ?" — on exclut volontairement les select comme
    // l'affectation, qui ont toujours une valeur par défaut (jamais
    // vraiment vides) et fausseraient la détection. On exclut aussi
    // plaignant_last_name/plaignant_first_name : ces deux champs sont
    // systématiquement pré-remplis par le serveur à partir du pseudo
    // Discord (voir app/ceam/routes.py), donc quasiment jamais vides —
    // les inclure ici empêchait la bannière de brouillon de s'afficher
    // pour la quasi-totalité des utilisateurs.
    const EMPTINESS_CHECK_FIELDS = [
      "concerne_last_name", "concerne_first_name",
      "location", "witness", "description", "proof",
    ];

    const isFormEmpty = () =>
      EMPTINESS_CHECK_FIELDS.every((name) => {
        const el = document.getElementById(name);
        return !el || !el.value.trim();
      });

    const saveDraft = () => {
      const data = {};
      DRAFT_FIELDS.forEach((name) => {
        const el = document.getElementById(name);
        if (el) data[name] = el.value;
      });
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ data, savedAt: Date.now() }));
      } catch (e) {
        // Stockage plein ou indisponible (navigation privée) : tant pis,
        // pas bloquant pour le reste du formulaire.
      }
    };

    const loadDraft = () => {
      try {
        const raw = localStorage.getItem(DRAFT_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    };

    const clearDraft = () => {
      try {
        localStorage.removeItem(DRAFT_KEY);
      } catch (e) {
        // rien à faire
      }
    };

    const applyDraft = (draft) => {
      DRAFT_FIELDS.forEach((name) => {
        const el = document.getElementById(name);
        if (el && draft.data[name]) el.value = draft.data[name];
      });
    };

    // Ne proposer la restauration que si le formulaire est actuellement
    // vide — s'il est déjà rempli (pré-remplissage Discord, ou
    // réaffichage après une erreur de validation serveur), on ne veut
    // surtout pas écraser ce qui est déjà correctement affiché.
    const banner = document.getElementById("draft-banner");
    const existingDraft = loadDraft();
    if (existingDraft && isFormEmpty() && banner) {
      banner.classList.add("is-visible");
      banner.querySelector("[data-restore-draft]")?.addEventListener("click", () => {
        applyDraft(existingDraft);
        banner.classList.remove("is-visible");
      });
      banner.querySelector("[data-dismiss-draft]")?.addEventListener("click", () => {
        clearDraft();
        banner.classList.remove("is-visible");
      });
    }

    // Sauvegarde continue pendant la saisie, avec un léger anti-rebond
    // pour ne pas écrire dans localStorage à chaque frappe.
    let draftSaveTimeout;
    DRAFT_FIELDS.forEach((name) => {
      const el = document.getElementById(name);
      el?.addEventListener("input", () => {
        clearTimeout(draftSaveTimeout);
        draftSaveTimeout = setTimeout(saveDraft, 500);
      });
      el?.addEventListener("change", saveDraft);
    });

    // À l'envoi du formulaire, le brouillon local n'a plus lieu d'être.
    depotForm.addEventListener("submit", clearDraft);
  }

  // ── Formulaire de dépôt "gamifié" en étapes plein écran ──
  // Chaque section (.wizard-step) prend toute la place et disparaît
  // complètement avant que la suivante n'apparaisse (transition
  // séquentielle, pas de chevauchement) — avec une barre de progression
  // en haut du formulaire qui reflète l'avancement, des points cliquables
  // pour revenir directement à une étape déjà atteinte, et une dernière
  // étape récapitulative qui relit les champs remplis avant l'envoi.
  const wizardForm = document.querySelector("[data-wizard]");
  if (wizardForm) {
    const steps = Array.from(wizardForm.querySelectorAll("[data-wizard-step]"));
    const progressFill = document.getElementById("wizard-progress-fill");
    const progressLabel = document.getElementById("wizard-progress-label");
    const progressDots = document.getElementById("wizard-progress-dots");
    const summaryEl = document.getElementById("wizard-summary");
    const ANIMATION_MS = 350;
    let currentIndex = 0;
    let furthestVisited = 0;
    let isAnimating = false;

    // Groupes de champs à relire à l'étape "Relire avant d'envoyer",
    // avec pour chacun le numéro de l'étape où le modifier. Les valeurs
    // sont lues directement dans le DOM au moment de l'affichage du
    // récapitulatif, pas dupliquées ici.
    const SUMMARY_SECTIONS = [
      { step: 0, label: "Plaignant", fields: [
        { id: "plaignant_last_name", label: "Nom" },
        { id: "plaignant_first_name", label: "Prénom" },
        { id: "plaignant_rank", label: "Grade" },
        { id: "plaignant_affectation", label: "Affectation" },
      ] },
      { step: 1, label: "Mis en cause", fields: [
        { id: "concerne_last_name", label: "Nom" },
        { id: "concerne_first_name", label: "Prénom" },
        { id: "concerne_rank", label: "Grade" },
        { id: "concerne_affectation", label: "Affectation" },
      ] },
      { step: 2, label: "Circonstances de l'incident", fields: [
        { id: "event_date", label: "Date" },
        { id: "event_hour", label: "Heure" },
        { id: "location", label: "Lieu" },
      ] },
      { step: 3, label: "Exposé des faits", fields: [
        { id: "description", label: "Description", long: true },
      ] },
      { step: 4, label: "Témoins de l'incident", fields: [
        { id: "witness", label: "Témoins", emptyText: "Aucun renseigné" },
      ] },
      { step: 5, label: "Preuves", fields: [
        { id: "proof", label: "Liens", emptyText: "Aucun lien renseigné", long: true },
      ], filesId: "proof_files" },
    ];

    const escapeHtml = (str) =>
      String(str).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      }[c]));

    const renderSummary = () => {
      if (!summaryEl) return;
      summaryEl.innerHTML = SUMMARY_SECTIONS.map((section) => {
        const rows = section.fields.map((f) => {
          const el = document.getElementById(f.id);
          let value = el ? el.value.trim() : "";
          if (!value) {
            value = f.emptyText || "Non renseigné";
          } else if (f.long && value.length > 160) {
            value = `${value.slice(0, 160)}…`;
          }
          return `<div class="wizard-summary__row"><span class="wizard-summary__label">${escapeHtml(f.label)}</span><span class="wizard-summary__value">${escapeHtml(value)}</span></div>`;
        }).join("");

        let filesRow = "";
        if (section.filesId) {
          const filesEl = document.getElementById(section.filesId);
          const count = filesEl && filesEl.files ? filesEl.files.length : 0;
          filesRow = `<div class="wizard-summary__row"><span class="wizard-summary__label">Fichiers joints</span><span class="wizard-summary__value">${count ? `${count} fichier(s)` : "Aucun"}</span></div>`;
        }

        return `
          <div class="wizard-summary__section">
            <div class="wizard-summary__section-header">
              <h3>${escapeHtml(section.label)}</h3>
              <button type="button" class="btn-ghost btn-sm" data-summary-edit="${section.step}">Modifier</button>
            </div>
            ${rows}${filesRow}
          </div>`;
      }).join("");

      summaryEl.querySelectorAll("[data-summary-edit]").forEach((btn) => {
        btn.addEventListener("click", () => {
          navigateToStep(parseInt(btn.dataset.summaryEdit, 10));
        });
      });
    };

    const updateProgress = () => {
      const percent = steps.length > 1 ? (currentIndex / (steps.length - 1)) * 100 : 100;
      if (progressFill) progressFill.style.width = `${percent}%`;
      if (progressLabel) {
        const title = steps[currentIndex].dataset.title || "";
        progressLabel.textContent = `Étape ${currentIndex + 1} / ${steps.length} — ${title}`;
      }
    };

    const renderDots = () => {
      if (!progressDots) return;
      progressDots.innerHTML = "";
      const lastIndex = steps.length - 1;
      steps.forEach((step, i) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "wizard-progress__dot";
        if (i === currentIndex) dot.classList.add("is-current");
        if (i < currentIndex) dot.classList.add("is-completed");
        const reachable = i <= furthestVisited;
        dot.disabled = !reachable;
        dot.title = step.dataset.title || `Étape ${i + 1}`;
        dot.setAttribute("aria-label", `Aller à l'étape ${i + 1} : ${dot.title}`);
        // Même formule que updateProgress() pour le remplissage : le
        // point de l'étape i est toujours exactement là où la barre
        // s'arrête quand currentIndex === i.
        const percent = lastIndex > 0 ? (i / lastIndex) * 100 : 0;
        dot.style.left = `${percent}%`;
        if (reachable) {
          dot.addEventListener("click", () => navigateToStep(i));
        }
        progressDots.appendChild(dot);
      });
    };

    // On ne valide "à la main" que les champs marqués required — la
    // validation complète (Optional/DataRequired réels) reste faite
    // côté serveur, ceci n'est qu'un garde-fou pour éviter d'avancer
    // avec une étape manifestement incomplète.
    const validateStep = (step) => {
      const fields = step.querySelectorAll("input[required], select[required], textarea[required]");
      for (const field of fields) {
        if (!field.checkValidity()) {
          field.reportValidity();
          return false;
        }
      }
      return true;
    };

    const goToStep = (targetIndex) => {
      if (isAnimating || targetIndex < 0 || targetIndex >= steps.length || targetIndex === currentIndex) return;
      isAnimating = true;

      const direction = targetIndex > currentIndex ? "next" : "prev";
      const outgoing = steps[currentIndex];
      const incoming = steps[targetIndex];
      const exitClass = direction === "next" ? "is-exiting-forward" : "is-exiting-back";
      const enterClass = direction === "next" ? "is-entering-forward" : "is-entering-back";

      wizardForm.scrollIntoView({ behavior: "smooth", block: "start" });
      outgoing.classList.add(exitClass);

      window.setTimeout(() => {
        outgoing.classList.remove("is-active", exitClass);
        incoming.classList.add("is-active", enterClass);
        if (incoming.hasAttribute("data-wizard-recap")) renderSummary();
        window.setTimeout(() => {
          incoming.classList.remove(enterClass);
          isAnimating = false;
        }, ANIMATION_MS);
      }, ANIMATION_MS);

      currentIndex = targetIndex;
      furthestVisited = Math.max(furthestVisited, targetIndex);
      updateProgress();
      renderDots();
    };

    // Navigation "libre" (points de progression, liens "Modifier" du
    // récapitulatif) : pas de validation à re-passer, puisqu'on ne peut
    // cibler qu'une étape déjà atteinte (voir reachable dans renderDots).
    const navigateToStep = (targetIndex) => goToStep(targetIndex);

    steps.forEach((step, index) => {
      step.classList.toggle("is-active", index === 0);
      step.querySelector("[data-wizard-next]")?.addEventListener("click", () => {
        if (!validateStep(step)) return;
        goToStep(index + 1);
      });
      step.querySelector("[data-wizard-prev]")?.addEventListener("click", () => {
        goToStep(index - 1);
      });
    });

    updateProgress();
    renderDots();
  }

  // ── Mentions "@Nom" dans les messages internes (échanges + réponse) ──
  // Un seul menu déroulant partagé (créé à la volée, ajouté au <body>)
  // réutilisé pour n'importe quelle zone de texte marquée
  // .js-mention-input — plus simple qu'un menu par zone de texte, et
  // évite les soucis de z-index avec les modals (réponse officielle).
  (function initMentionAutocomplete() {
    const dataEl = document.getElementById("ceam-mentionable-members");
    if (!dataEl) return;

    let memberNames = [];
    try {
      memberNames = JSON.parse(dataEl.textContent) || [];
    } catch (e) {
      return;
    }
    if (!memberNames.length) return;

    const inputs = Array.from(document.querySelectorAll("textarea.js-mention-input"));
    if (!inputs.length) return;

    const menu = document.createElement("div");
    menu.className = "mention-autocomplete";
    menu.setAttribute("role", "listbox");
    document.body.appendChild(menu);

    let activeInput = null;
    let activeMatches = [];
    let activeIndex = 0;
    let mentionStart = -1; // position du "@" déclencheur dans activeInput.value

    const closeMenu = () => {
      menu.classList.remove("is-visible");
      activeInput = null;
      activeMatches = [];
      mentionStart = -1;
    };

    const renderMenu = () => {
      menu.innerHTML = "";
      activeMatches.forEach((name, i) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "mention-autocomplete__item" + (i === activeIndex ? " is-active" : "");
        item.textContent = name;
        item.addEventListener("mousedown", (e) => {
          // mousedown (pas click) pour agir AVANT que le textarea ne
          // perde le focus (blur), qui sinon fermerait le menu en premier.
          e.preventDefault();
          selectMention(name);
        });
        menu.appendChild(item);
      });
    };

    const positionMenu = (input) => {
      const rect = input.getBoundingClientRect();
      menu.style.left = `${rect.left + window.scrollX}px`;
      menu.style.top = `${rect.bottom + window.scrollY + 4}px`;
      menu.style.width = `${Math.min(rect.width, 320)}px`;
    };

    const selectMention = (name) => {
      if (!activeInput || mentionStart < 0) return;
      const value = activeInput.value;
      const caret = activeInput.selectionStart;
      const before = value.slice(0, mentionStart);
      const after = value.slice(caret);
      const inserted = `@${name} `;
      activeInput.value = before + inserted + after;
      const newCaret = before.length + inserted.length;
      activeInput.focus();
      activeInput.setSelectionRange(newCaret, newCaret);
      // Un input "réel" pour que le reste du JS (ex: brouillon) capte le
      // changement de contenu comme s'il avait été tapé.
      activeInput.dispatchEvent(new Event("input", { bubbles: true }));
      closeMenu();
    };

    const updateMatches = (input) => {
      const value = input.value;
      const caret = input.selectionStart;
      const uptoCaret = value.slice(0, caret);
      const triggerIndex = uptoCaret.lastIndexOf("@");
      if (triggerIndex === -1) return closeMenu();

      const between = uptoCaret.slice(triggerIndex + 1, caret);
      // Le texte entre "@" et le curseur ne doit contenir aucun espace —
      // sinon ce n'est plus une mention en cours de frappe.
      if (/\s/.test(between)) return closeMenu();
      // Le "@" doit démarrer un mot (début de texte, ou précédé d'un
      // espace) pour ne pas se déclencher sur un email ou un pseudo
      // Discord collé (ex: "contact@exemple.com").
      const charBefore = triggerIndex > 0 ? value[triggerIndex - 1] : "";
      if (charBefore && !/\s/.test(charBefore)) return closeMenu();

      const query = between.toLowerCase();
      const matches = memberNames
        .filter((name) => name.toLowerCase().includes(query))
        .slice(0, 6);
      if (!matches.length) return closeMenu();

      activeInput = input;
      activeMatches = matches;
      activeIndex = 0;
      mentionStart = triggerIndex;
      positionMenu(input);
      renderMenu();
      menu.classList.add("is-visible");
    };

    inputs.forEach((input) => {
      input.addEventListener("input", () => updateMatches(input));
      input.addEventListener("click", () => updateMatches(input));
      input.addEventListener("blur", () => {
        // Délai court : laisse le mousedown d'un item du menu s'exécuter
        // avant que le menu ne se ferme (sinon le clic n'atteint jamais
        // le bouton, déjà retiré du DOM par la fermeture).
        window.setTimeout(closeMenu, 120);
      });
      input.addEventListener("keydown", (e) => {
        if (activeInput !== input || !activeMatches.length) return;
        if (e.key === "ArrowDown") {
          e.preventDefault();
          activeIndex = (activeIndex + 1) % activeMatches.length;
          renderMenu();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          activeIndex = (activeIndex - 1 + activeMatches.length) % activeMatches.length;
          renderMenu();
        } else if (e.key === "Enter" || e.key === "Tab") {
          e.preventDefault();
          selectMention(activeMatches[activeIndex]);
        } else if (e.key === "Escape") {
          closeMenu();
        }
      });
    });

    window.addEventListener("scroll", () => {
      if (activeInput) positionMenu(activeInput);
    }, true);
  })();

  // ── Sidebar réductible ──
  const sidebarToggle = document.getElementById("sidebar-collapse-toggle");
  if (sidebarToggle) {
    const COLLAPSE_KEY = "ceam-sidebar-collapsed";
    sidebarToggle.addEventListener("click", () => {
      const isCollapsed = document.documentElement.getAttribute("data-sidebar-collapsed") === "true";
      const next = !isCollapsed;
      if (next) {
        document.documentElement.setAttribute("data-sidebar-collapsed", "true");
      } else {
        document.documentElement.removeAttribute("data-sidebar-collapsed");
      }
      try {
        localStorage.setItem(COLLAPSE_KEY, String(next));
      } catch (e) {
        // stockage indisponible (navigation privée) : l'état reste actif
        // pour cette session, juste pas mémorisé pour la prochaine visite.
      }
    });
  }

  // ── Apparition au scroll ──
  // Les éléments marqués data-reveal (cards du Règlement, de l'Accueil…)
  // apparaissent en fondu + léger glissement dès qu'ils entrent dans le
  // viewport, une seule fois (pas de réapparition en remontant). Si
  // l'utilisateur préfère moins d'animations (prefers-reduced-motion),
  // le CSS les affiche directement sans transition — on n'a rien de plus
  // à faire ici dans ce cas.
  const revealTargets = document.querySelectorAll("[data-reveal]");
  if (revealTargets.length && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealTargets.forEach((el, index) => {
      // Léger effet de cascade pour les éléments d'une même grille
      // (missions de l'accueil, sections du règlement) : chacun apparaît
      // un peu après le précédent plutôt que tous d'un coup.
      const group = el.closest("[data-reveal-group]");
      const delayIndex = group ? Array.from(group.querySelectorAll("[data-reveal]")).indexOf(el) : 0;
      el.style.transitionDelay = `${Math.min(delayIndex, 6) * 70}ms`;
      revealObserver.observe(el);
    });
  } else {
    // Navigateur sans IntersectionObserver (très rare) : afficher direct.
    revealTargets.forEach((el) => el.classList.add("is-revealed"));
  }

  // ── Bascule entre conversations (onglet Échanges) ──
  // Même principe que les onglets Rapport/Échanges/Instruction : un clic
  // sur une conversation affiche son panneau (messages + composer propre
  // à ce fil précis) et masque les autres.
  const conversationTriggers = document.querySelectorAll("[data-conversation-trigger]");
  const conversationPanels = document.querySelectorAll("[data-conversation-panel]");
  if (conversationTriggers.length && conversationPanels.length) {
    const activateConversation = (key) => {
      conversationPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.conversationPanel === key);
      });
      conversationTriggers.forEach((btn) => {
        btn.classList.toggle("is-active", btn.dataset.conversationTrigger === key);
      });
      const chatArea = document.querySelector('[data-conversation-panel="' + key + '"] [data-chat-scroll]');
      if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
    };

    conversationTriggers.forEach((btn) => {
      btn.addEventListener("click", () => activateConversation(btn.dataset.conversationTrigger));
    });
  }

  // ── Envoyer un message avec Ctrl+Entrée (Cmd+Entrée sur Mac) ──
  document.querySelectorAll(".chat-panel__composer textarea").forEach((textarea) => {
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        const form = textarea.closest("form");
        // Ne rien faire si le formulaire est déjà en cours d'envoi (le
        // bouton est alors désactivé par la protection anti double-clic).
        const submitBtn = form?.querySelector('button[type="submit"]');
        if (form && !submitBtn?.disabled) {
          form.requestSubmit ? form.requestSubmit() : form.submit();
        }
      }
    });
  });

  // ── Suppression d'un message (clic droit -> menu -> confirmation) ──
  // Réservé aux messages qu'on a soi-même écrits (data-message-id n'est
  // même pas présent sur les anciens messages envoyés avant cette
  // fonctionnalité, ni sur les réponses officielles "Commission CEAM" —
  // ils ne sont donc jamais proposés à la suppression ici. Le serveur
  // revérifie de toute façon qui est l'auteur avant de supprimer quoi
  // que ce soit ; ce menu n'est qu'un raccourci, pas la sécurité.
  const contextMenu = document.getElementById("chat-message-context-menu");
  const deleteForm = document.getElementById("chat-delete-message-form");
  const chatPanel = document.querySelector(".chat-panel");
  const canDeleteAny = chatPanel ? chatPanel.dataset.canDeleteAny === "true" : false;
  if (contextMenu && deleteForm) {
    let targetMessageId = null;
    let targetItemElement = null;

    const hideContextMenu = () => {
      contextMenu.hidden = true;
      targetMessageId = null;
      targetItemElement = null;
    };

    // Délégation d'événements sur `document` plutôt qu'un écouteur par
    // carte : une carte insérée par le sondage automatique (qui remplace
    // le contenu HTML toutes les quelques secondes, voir plus bas) n'a
    // jamais eu l'occasion de recevoir un addEventListener individuel --
    // avec la délégation, ce clic droit fonctionne quand même, puisque
    // `document` est toujours là et qu'on cherche la carte concernée au
    // moment du clic, pas à l'avance.
    document.addEventListener("contextmenu", (event) => {
      const bubble = event.target.closest(".chat-message__bubble");
      if (!bubble) {
        hideContextMenu();
        return;
      }

      // Le président CEAM / admin (canDeleteAny) peut faire un clic
      // droit sur N'IMPORTE QUELLE carte, pas seulement les siennes —
      // le serveur revérifie de toute façon le rôle réel avant
      // d'accepter la suppression, ceci n'est que l'affichage du menu.
      const isMine = !!bubble.closest(".chat-message--mine");
      if (!isMine && !canDeleteAny) return; // pas notre carte, et pas de privilège

      // Cible le message précis sous le curseur si le clic droit tombe
      // dedans (utile quand plusieurs messages sont regroupés dans la
      // même carte) ; sinon (survol de l'en-tête, d'un espace vide...),
      // retombe sur le dernier message de la carte, le plus visible.
      const items = bubble.querySelectorAll(".chat-message__item");
      const clickedItem = event.target.closest(".chat-message__item");
      const targetItem = clickedItem || items[items.length - 1];
      const messageId = targetItem ? targetItem.dataset.messageId : null;
      if (!messageId) return; // trop ancien pour être supprimable

      event.preventDefault();
      targetMessageId = messageId;
      targetItemElement = targetItem;

      const menuWidth = 180;
      const menuHeight = 44;
      let x = event.clientX;
      let y = event.clientY;
      if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 8;
      if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 8;
      contextMenu.style.left = `${x}px`;
      contextMenu.style.top = `${y}px`;
      contextMenu.hidden = false;
    });

    document.addEventListener("click", hideContextMenu);
    window.addEventListener("scroll", hideContextMenu, true);
    window.addEventListener("resize", hideContextMenu);

    const deleteButton = contextMenu.querySelector("[data-context-menu-delete]");
    const editButton = contextMenu.querySelector("[data-context-menu-edit]");
    const editModal = document.getElementById("edit-message-modal");
    editButton.addEventListener("click", () => {
      const messageId = targetMessageId;
      const itemElement = targetItemElement;
      hideContextMenu();
      if (!messageId || !itemElement || !editModal) return;
      editModal.querySelector("#edit-message-id").value = messageId;
      const textarea = editModal.querySelector("#edit-message-content");
      textarea.value = itemElement.dataset.content || "";
      editModal.classList.add("is-visible");
      editModal.setAttribute("aria-hidden", "false");
      textarea.focus();
    });

    deleteButton.addEventListener("click", () => {
      const messageId = targetMessageId;
      hideContextMenu();
      if (!messageId) return;
      const confirmed = window.confirm("Supprimer définitivement ce message ? Cette action est irréversible.");
      if (!confirmed) return;
      deleteForm.querySelector('[name="message_id"]').value = messageId;
      deleteForm.submit();
    });
  }

  // ── Rafraîchissement automatique du fil actif (sans recharger la page) ──
  // Revérifie régulièrement s'il y a du nouveau sur la conversation
  // affichée : un message qui vient d'arriver, le badge "Nouveau" qui
  // doit disparaître une fois lu, les flèches de vu qui passent au doré
  // dès que l'autre personne a ouvert le message — tout ça sans que
  // personne n'ait besoin de rafraîchir la page (ni de vider son cache :
  // ce sont des données fraîches à chaque appel, jamais mises en cache).
  if (chatPanel && conversationPanels.length) {
    const rapportId = chatPanel.dataset.rapportId;
    let isRefreshing = false;

    const isNearBottom = (el) => el.scrollHeight - el.scrollTop - el.clientHeight < 80;

    const refreshActiveConversation = async () => {
      // Pas de sondage si l'onglet du navigateur est en arrière-plan
      // (économise des requêtes inutiles), ou si un rafraîchissement est
      // déjà en cours (évite d'empiler les appels si le réseau est lent).
      if (isRefreshing || document.hidden || !rapportId) return;
      // Ne pas remplacer le contenu pendant qu'un menu contextuel ou le
      // modal d'édition sont ouverts sur ce fil -- ça casserait la cible
      // du clic droit en cours (l'élément DOM visé disparaîtrait).
      const contextMenuOpen = contextMenu && !contextMenu.hidden;
      const editModalOpen = document.getElementById("edit-message-modal")?.classList.contains("is-visible");
      if (contextMenuOpen || editModalOpen) return;
      const activePanel = document.querySelector("[data-conversation-panel].is-active");
      if (!activePanel) return;
      const threadKey = activePanel.dataset.conversationPanel;
      const messagesArea = activePanel.querySelector("[data-chat-scroll]");
      if (!threadKey || !messagesArea) return;

      isRefreshing = true;
      try {
        const wasNearBottom = isNearBottom(messagesArea);
        const resp = await fetch(`/ceam/dossier/${rapportId}/fil/${encodeURIComponent(threadKey)}/fragment`);
        if (resp.ok) {
          const html = await resp.text();
          // Ne toucher au DOM que si le contenu a réellement changé --
          // évite de perturber une sélection de texte ou une interaction
          // en cours pour rien à chaque sondage.
          if (html !== messagesArea.dataset.lastHtml) {
            messagesArea.innerHTML = html;
            messagesArea.dataset.lastHtml = html;
            if (wasNearBottom) messagesArea.scrollTop = messagesArea.scrollHeight;
          }
        }
      } catch (e) {
        // Silencieux : un souci réseau ponctuel ne doit jamais gêner la
        // navigation, le prochain sondage réessaiera de lui-même.
      } finally {
        isRefreshing = false;
      }
    };

    setInterval(refreshActiveConversation, 4000);
    // Revenir sur l'onglet du navigateur déclenche aussi un rafraîchissement
    // immédiat, sans attendre le prochain cycle de 4 secondes.
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) refreshActiveConversation();
    });
    // Changer de conversation rafraîchit aussi immédiatement celle qui
    // vient de s'ouvrir, sans attendre.
    conversationTriggers.forEach((btn) => {
      btn.addEventListener("click", () => setTimeout(refreshActiveConversation, 300));
    });
  }
})();