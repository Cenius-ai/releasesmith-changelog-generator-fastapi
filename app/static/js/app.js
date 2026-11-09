/* Releasesmith - progressive enhancement only.
   Every flow works without JavaScript; this file adds the affordances that
   genuinely need the browser: show/hide password, copy the Markdown export,
   and a re-entrancy guard on form submits. */
(function () {
  "use strict";

  var COPY_LABEL_RESET_MS = 2000;

  function togglePassword(button) {
    var input = document.getElementById(button.getAttribute("data-toggle-password"));
    if (!input) {
      return;
    }
    var hidden = input.getAttribute("type") === "password";
    input.setAttribute("type", hidden ? "text" : "password");
    button.textContent = hidden ? "Hide" : "Show";
    button.setAttribute("aria-pressed", hidden ? "true" : "false");
    button.setAttribute("aria-label", hidden ? "Hide password" : "Show password");
    input.focus();
  }

  function legacyCopy(target) {
    var selection = window.getSelection();
    var range = document.createRange();
    range.selectNodeContents(target);
    selection.removeAllRanges();
    selection.addRange(range);
    var copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (error) {
      copied = false;
    }
    selection.removeAllRanges();
    return copied;
  }

  function copyMarkdown(button) {
    var target = document.getElementById(button.getAttribute("data-copy-target"));
    var status = document.getElementById("copy-status");
    if (!target) {
      return;
    }
    var text = target.textContent;

    function confirmCopy(ok) {
      if (status) {
        status.textContent = ok
          ? "Markdown copied to the clipboard."
          : "Copy failed - select the text and copy manually.";
      }
      if (!ok) {
        return;
      }
      var original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(function () {
        button.textContent = original;
      }, COPY_LABEL_RESET_MS);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () {
          confirmCopy(true);
        },
        function () {
          confirmCopy(legacyCopy(target));
        }
      );
      return;
    }
    confirmCopy(legacyCopy(target));
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-toggle-password]");
    if (toggle) {
      togglePassword(toggle);
      return;
    }
    var copy = event.target.closest("[data-copy-target]");
    if (copy) {
      copyMarkdown(copy);
    }
  });

  function busyLabel(form, submitter) {
    if (form.getAttribute("data-submitting") === "1") {
      return true;
    }
    form.setAttribute("data-submitting", "1");
    var button = submitter || form.querySelector('button[type="submit"]');
    if (button && button.getAttribute("data-busy")) {
      var label = button.getAttribute("data-busy");
      window.setTimeout(function () {
        button.textContent = label;
        button.setAttribute("aria-busy", "true");
        button.disabled = true;
      }, 50);
    }
    return false;
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") {
      return;
    }
    if (busyLabel(form, event.submitter)) {
      event.preventDefault();
    }
  });

  /* Restoring from the back/forward cache must not leave a dead submit button. */
  window.addEventListener("pageshow", function () {
    var forms = document.querySelectorAll("form");
    Array.prototype.forEach.call(forms, function (form) {
      form.removeAttribute("data-submitting");
      var buttons = form.querySelectorAll('button[type="submit"]');
      Array.prototype.forEach.call(buttons, function (button) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      });
    });
  });
})();
