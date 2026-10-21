/* Wheelwright Workshop Orders — progressive enhancement only.
   Every page and every form works without this file; it adds the
   show/hide password control, destructive confirmation and a
   double-submit guard. */
(function () {
  'use strict';

  function initPasswordToggles() {
    var buttons = document.querySelectorAll('[data-password-toggle]');
    Array.prototype.forEach.call(buttons, function (button) {
      var inputId = button.getAttribute('data-password-toggle');
      var input = inputId ? document.getElementById(inputId) : null;
      if (!input) {
        return;
      }
      button.addEventListener('click', function () {
        var revealed = input.type === 'text';
        input.type = revealed ? 'password' : 'text';
        button.textContent = revealed ? 'Show' : 'Hide';
        button.setAttribute('aria-pressed', revealed ? 'false' : 'true');
        button.setAttribute('aria-label', revealed ? 'Show password' : 'Hide password');
        input.focus();
      });
    });
  }

  function initConfirmForms() {
    var forms = document.querySelectorAll('form[data-confirm]');
    Array.prototype.forEach.call(forms, function (form) {
      form.addEventListener('submit', function (event) {
        var message = form.getAttribute('data-confirm') || 'Are you sure?';
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  }

  function initSubmitGuards() {
    var forms = document.querySelectorAll('form[data-guard]');
    Array.prototype.forEach.call(forms, function (form) {
      form.addEventListener('submit', function (event) {
        if (form.dataset.submitting === 'true') {
          event.preventDefault();
          return;
        }
        form.dataset.submitting = 'true';
        var button = form.querySelector('button[data-primary]');
        if (button) {
          window.setTimeout(function () {
            button.disabled = true;
          }, 0);
        }
      });
    });
  }

  function initFocusFirstError() {
    var invalid = document.querySelector('[aria-invalid="true"]');
    if (invalid && typeof invalid.focus === 'function') {
      invalid.focus();
    }
  }

  function init() {
    initPasswordToggles();
    initConfirmForms();
    initSubmitGuards();
    initFocusFirstError();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
