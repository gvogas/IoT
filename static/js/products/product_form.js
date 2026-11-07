// A barcode scanner types the number and then presses Enter. Don't let that Enter send the form: go to the next box
document.getElementById("upc").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    document.getElementById("active").focus();
});

// After a failed save, start at the first box with a problem
const firstProblem = document.querySelector(".is-invalid");
if (firstProblem) firstProblem.focus();

// Show the chosen image straight away, and stop a file that is too big before it is sent
const imageInput = document.getElementById("image");
const imagePreview = document.getElementById("image-preview");
const imageProblem = document.querySelector("[data-image-problem]");
const removeImage = document.getElementById("removeImage");
const savedPreview = imagePreview.innerHTML;

imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    imageProblem.hidden = true;
    imagePreview.innerHTML = savedPreview;
    if (!file) return;

    if (file.size > Number(imageInput.dataset.maxBytes)) {
        imageProblem.textContent = "That image is too big. Please choose a smaller one.";
        imageProblem.hidden = false;
        imageInput.value = "";
        return;
    }
    const picture = document.createElement("img");
    picture.className = "product-image lg";
    picture.alt = "Preview of the chosen image";
    picture.src = URL.createObjectURL(file);
    imagePreview.replaceChildren(picture);
    if (removeImage) removeImage.checked = false;
});
