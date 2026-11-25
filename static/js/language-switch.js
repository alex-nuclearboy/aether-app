"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const languagePicker = document.getElementById("site-language");

    if (!languagePicker) {
        return;
    }

    languagePicker.addEventListener("change", () => {
        languagePicker.form.requestSubmit();
    });
});
