// A barcode scanner types the number and then presses Enter. Don't let that Enter send the form: go to the next box
const upcInput = document.getElementById("upc");
upcInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    document.getElementById("name").focus();
});

// Warn straight away if another product already has this UPC. The server checks again when the form is saved
const upcTaken = document.querySelector("[data-upc-taken]");
upcInput.addEventListener("change", async () => {
    upcTaken.hidden = true;
    const upc = upcInput.value.trim();
    if (!upc) return;

    const params = new URLSearchParams({ upc });
    if (upcInput.dataset.productId) params.set("productID", upcInput.dataset.productId);
    try {
        const response = await fetch(`/api/products/upc-check?${params}`);
        const result = await response.json();
        if (!result.taken) return;
        const link = document.createElement("a");
        link.href = `/products/${result.productID}`;
        link.textContent = result.name;
        upcTaken.replaceChildren("This UPC is already used by ", link, ".");
        upcTaken.hidden = false;
    } catch {
        // No answer: nothing to show, the save still checks
    }
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
