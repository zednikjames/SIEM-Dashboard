const createUserForm = document.getElementById("create-user-form");
const notification = document.getElementById("admin-notification");
const notificationTitle = document.getElementById("notification-title");
const notificationMessage = document.getElementById("notification-message");
const notificationClose = notification.querySelector(".notification-close");

function showNotification(message, isError, action = "Action") {
    notification.classList.toggle("error", isError);
    notification.setAttribute("role", isError ? "alert" : "status");
    notificationTitle.textContent = isError ? `${action} failed` : `${action} completed`;
    notificationMessage.textContent = message;
    notification.hidden = false;
}

notificationClose.addEventListener("click", () => {
    notification.hidden = true;
});

createUserForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = createUserForm.querySelector('button[type="submit"]');
    button.disabled = true;

    try {
        const response = await fetch(createUserForm.action, {
            method: "POST",
            headers: { "Accept": "application/json" },
            body: new FormData(createUserForm),
        });
        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json") ? await response.json() : null;

        if (!response.ok) {
            showNotification(data?.error || `Request failed (${response.status}).`, true, "Create user");
        } else if (response.status === 201 && data?.message) {
            showNotification(data.message, false, "Create user");
            createUserForm.reset();
        } else {
            showNotification("Unexpected response from the server.", true, "Create user");
        }
    } catch (error) {
        console.error("Could not submit the create-user form:", error);
        showNotification("Could not contact the server. Please try again.", true, "Create user");
    } finally {
        button.disabled = false;
    }
});

const modifyUserForm = document.getElementById("modify-user-form");

modifyUserForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = modifyUserForm.querySelector('button[type="submit"]');
    button.disabled = true;

    try {
        const response = await fetch(modifyUserForm.action, {
            method: "POST",
            headers: { "Accept": "application/json" },
            body: new FormData(modifyUserForm),
        });

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
            ? await response.json()
            : null;

        if (!response.ok) {
            showNotification(data?.error || `Request failed (${response.status}).`, true, "Modify user");
        } else if (response.status === 200 && data?.message) {
            showNotification(data.message, false, "Modify user");
        } else {
            showNotification("Unexpected response from the server.", true, "Modify user");
        }
    } catch (error) {
        console.error("Could not submit the modify-user form:", error);
        showNotification("Could not contact the server. Please try again.", true, "Modify user");
    } finally {
        button.disabled = false;
    }
});