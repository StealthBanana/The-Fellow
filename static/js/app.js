document.addEventListener("DOMContentLoaded", () => {
    // For loading feature
    const form = document.querySelector("form");
    const loader = document.querySelector(".loader");
    const inputInfo = document.querySelector(".inputInfo");
    const loadInfo = document.getElementById("loadInfo");
    const inputTopic = document.getElementsByName('inputTopic')[0];

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        inputInfo.addEventListener("transitionend", () => {
            inputInfo.style.display = "none";

            loader.classList.remove("loader-hidden");
            loadInfo.textContent = `Getting resources on: ${inputTopic.value}`;
            loadInfo.style.visibility = "visible";

            form.submit();

        }, { once: true });

        inputInfo.classList.add("input-info-hidden");
    });


    // For suprise topic feature
    const surpriseForm = document.getElementById("surpriseForm");

    surpriseForm.addEventListener("submit", (event) => {
        // Same as above except now with confetti!
        event.preventDefault();

        // Confetti stuff here
        buttonPositon = surpriseForm.getBoundingClientRect();
        horizontalMid = (buttonPositon.left + buttonPositon.right) / 2 
        verticalMid =  (buttonPositon.top + buttonPositon.bottom) / 2 
        confetti({ position: { x: horizontalMid, y: verticalMid } });


        inputInfo.addEventListener("transitionend", () => {
            inputInfo.style.display = "none";

            loader.classList.remove("loader-hidden");
            loadInfo.textContent = `Getting resources on: YOU MUST FIX THIS PART BROOOOOOOOOOOOOOOOO`;
            loadInfo.style.visibility = "visible";

            surpriseForm.submit();

        }, { once: true });

        inputInfo.classList.add("input-info-hidden");
    });

});
