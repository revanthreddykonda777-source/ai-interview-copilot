document.addEventListener("DOMContentLoaded", function () {

    // Scope everything to the answer form; the nav's Sign Out form comes first in the page.
    const textarea = document.querySelector("textarea[name='user_answer']");
    if (!textarea) return;
    const form = textarea.closest("form");
    const button = form.querySelector("button[type='submit']");

    // Word Counter
    const counter = document.createElement("p");
    counter.id = "word-counter";
    counter.style.marginTop = "10px";
    counter.style.color = "#5f584f";
    counter.style.fontSize = "13px";
    counter.style.fontWeight = "600";
    counter.innerHTML = "Words: 0";

    textarea.insertAdjacentElement("afterend", counter);

    textarea.addEventListener("input", function () {

        const words = textarea.value.trim().split(/\s+/).filter(word => word.length > 0);

        counter.innerHTML = "Words: " + words.length;

    });

    form.addEventListener("submit", function (e) {

        if (textarea.value.trim() === "") {

            e.preventDefault();

            alert("Please enter your answer.");

            return;

        }

        button.disabled = true;

        button.innerHTML = "Evaluating...";

    });

});