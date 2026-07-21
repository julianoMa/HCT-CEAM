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
    // vraiment vides) et fausseraient la détection.
    const EMPTINESS_CHECK_FIELDS = [
      "plaignant_last_name", "plaignant_first_name",
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

    document.querySelectorAll(".chat-message__bubble").forEach((bubble) => {
      bubble.addEventListener("contextmenu", (event) => {
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
    });

    document.addEventListener("click", hideContextMenu);
    document.addEventListener("contextmenu", (event) => {
      if (!event.target.closest(".chat-message__bubble")) hideContextMenu();
    });
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