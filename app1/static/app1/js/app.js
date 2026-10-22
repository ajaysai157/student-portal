/* College Management Portal - small progressive enhancements.
 *
 * The portal works without JavaScript: forms submit normally, the delete
 * confirmation is a separate page and the navigation is plain links. This
 * file only adds convenience on top of that.
 */
(function () {
    "use strict";

    /* Mobile navigation -------------------------------------------------- */
    var toggle = document.querySelector(".nav-toggle");
    var sidebar = document.getElementById("sidebar");

    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            var open = sidebar.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });

        // Close the menu when a link inside it is used or the viewport grows.
        sidebar.addEventListener("click", function (event) {
            if (event.target.closest("a")) {
                sidebar.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 960) {
                sidebar.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    /* Dismissible messages ---------------------------------------------- */
    document.addEventListener("click", function (event) {
        var close = event.target.closest(".message-close");
        if (close) {
            var message = close.closest(".message");
            if (message) {
                message.remove();
            }
        }
    });

    /* Auto hide success messages after a while ---------------------------- */
    window.setTimeout(function () {
        document.querySelectorAll(".message-success").forEach(function (message) {
            message.style.transition = "opacity 0.4s ease";
            message.style.opacity = "0";
            window.setTimeout(function () {
                message.remove();
            }, 400);
        });
    }, 6000);

    /* Image preview before uploading a photo ----------------------------- */
    var photoInput = document.getElementById("id_student_image");
    var preview = document.getElementById("imagePreview");

    if (photoInput && preview) {
        photoInput.addEventListener("change", function () {
            var file = photoInput.files && photoInput.files[0];
            if (!file) {
                return;
            }
            var reader = new FileReader();
            reader.onload = function (event) {
                preview.src = event.target.result;
                preview.style.display = "block";
            };
            reader.readAsDataURL(file);
        });
    }

    /* Confirm destructive submits that are not on a confirmation page ----- */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        });
    });
})();
