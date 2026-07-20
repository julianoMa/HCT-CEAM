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
})();