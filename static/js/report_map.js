/* Optional AI photo assistant: resizes picked photo client-side and queries /api/suggest/. */
(function () {
  const photoInput = document.querySelector("input[name='photos']");
  const categorySelect = document.querySelector("select[name='category']");
  const severitySelect = document.querySelector("select[name='severity']");
  const aiLabelInput = document.querySelector("input[name='ai_label']");
  const aiConfInput = document.querySelector("input[name='ai_confidence']");
  const banner = document.getElementById("ai-suggestion-banner");
  const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']");

  if (!photoInput) return;

  function resizeToJpegBlob(file, maxDim, quality) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = function () {
        try {
          let w = img.width;
          let h = img.height;
          if (w > maxDim || h > maxDim) {
            if (w >= h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0, w, h);
          canvas.toBlob(
            (blob) => {
              URL.revokeObjectURL(url);
              if (blob) resolve(blob);
              else reject(new Error("Canvas toBlob failed"));
            },
            "image/jpeg",
            quality
          );
        } catch (err) {
          URL.revokeObjectURL(url);
          reject(err);
        }
      };
      img.onerror = function (err) {
        URL.revokeObjectURL(url);
        reject(err);
      };
      img.src = url;
    });
  }

  photoInput.addEventListener("change", async function () {
    const file = photoInput.files && photoInput.files[0];
    if (!file) return;

    try {
      const blob = await resizeToJpegBlob(file, 800, 0.8);
      const fd = new FormData();
      fd.append("image", blob, "preview.jpg");

      const headers = {};
      if (csrfInput && csrfInput.value) {
        headers["X-CSRFToken"] = csrfInput.value;
      }

      const resp = await fetch("/api/suggest/", {
        method: "POST",
        headers: headers,
        body: fd,
      });
      if (!resp.ok) return;
      const data = await resp.json();
      const s = data && data.suggestion;
      if (!s) return;

      if (categorySelect) {
        if (s.category_id) {
          categorySelect.value = String(s.category_id);
        } else if (s.category) {
          for (const opt of categorySelect.options) {
            if (opt.text.trim().toLowerCase() === s.category.trim().toLowerCase()) {
              categorySelect.value = opt.value;
              break;
            }
          }
        }
        categorySelect.dispatchEvent(new Event("change"));
      }

      if (severitySelect && s.severity) {
        severitySelect.value = String(s.severity);
      }

      if (aiLabelInput && s.category) {
        aiLabelInput.value = s.category;
      }
      if (aiConfInput && s.confidence !== undefined && s.confidence !== null) {
        aiConfInput.value = String(s.confidence);
      }

      if (banner) {
        const confPct =
          s.confidence !== undefined && s.confidence !== null
            ? ` (${Math.round(Number(s.confidence) * 100)}% confidence)`
            : "";
        banner.textContent = `AI suggestion, please confirm: ${s.category || ""}${confPct}.`;
        banner.style.display = "block";
      }
    } catch (_) {
      // Fail silently; form behaves normally without AI.
    }
  });
})();
