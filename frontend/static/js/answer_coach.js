document.addEventListener("DOMContentLoaded", function () {

    const form = document.querySelector("form");
    const textarea = document.querySelector("textarea");
    const button = document.querySelector("button[type='submit']");

    // Word Counter
    const counter = document.createElement("p");
    counter.id = "word-counter";
    counter.style.marginTop = "10px";
    counter.style.color = "#5f584f";
    counter.style.fontSize = "13px";
    counter.style.fontWeight = "600";
    counter.innerHTML = "Words: 0";

    textarea.parentNode.insertBefore(counter, button);

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