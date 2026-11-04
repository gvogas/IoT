// Show each notification after an action. Bootstrap's toast fades out by itself after its delay
document.querySelectorAll(".toast[data-delay]").forEach((element) => {
    new bootstrap.Toast(element, { delay: Number(element.dataset.delay) }).show();
});
