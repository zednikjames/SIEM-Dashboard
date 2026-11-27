const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function setup() {
    function makeForm(action) {
        return {
            action,
            button: { disabled: false },
            addEventListener(event, handler) { this[event] = handler; },
            querySelector() { return this.button; },
            reset() { this.resetCalled = true; },
        };
    }

    const create = makeForm("/api/create_user");
    const modify = makeForm("/api/modify_user");
    const close = { addEventListener(event, handler) { this[event] = handler; } };
    const notification = {
        hidden: true,
        classList: { toggle(name, value) { notification.error = value; } },
        setAttribute(name, value) { this[name] = value; },
        querySelector() { return close; },
    };
    const title = {};
    const message = {};
    const elements = {
        "create-user-form": create,
        "modify-user-form": modify,
        "admin-notification": notification,
        "notification-title": title,
        "notification-message": message,
    };
    let fetchHandler;
    const refreshes = { users: 0, logs: 0 };
    const context = {
        document: { getElementById(id) { return elements[id]; } },
        FormData: class { constructor(form) { this.form = form; } },
        fetch: (...args) => fetchHandler(...args),
        async loadUsers() { refreshes.users++; },
        async loadAuditLogs() { refreshes.logs++; },
        console: { error() {} },
    };
    const script = fs.readFileSync(
        path.join(__dirname, "..", "src", "static", "js", "administration-notifications.js"),
        "utf8",
    );
    vm.runInNewContext(script, context);
    return {
        create, modify, close, notification, title, message, refreshes,
        setFetch(handler) { fetchHandler = handler; },
    };
}

function response(status, data) {
    return {
        ok: status >= 200 && status < 300,
        status,
        headers: { get() { return "application/json"; } },
        async json() { return data; },
    };
}

test("both forms show action-specific success and failure notifications", async () => {
    const ui = setup();
    for (const [form, action, status] of [
        [ui.create, "Create user", 201],
        [ui.modify, "Modify user", 200],
    ]) {
        ui.setFetch(async (url, options) => {
            assert.equal(url, form.action);
            assert.equal(options.body.form, form);
            assert.equal(form.button.disabled, true);
            return response(status, { message: "Saved" });
        });
        await form.submit({ preventDefault() {} });
        assert.equal(ui.notification.hidden, false);
        assert.equal(ui.notification.error, false);
        assert.equal(ui.title.textContent, `${action} completed`);
        assert.equal(ui.message.textContent, "Saved");
        assert.equal(form.button.disabled, false);

        ui.setFetch(async () => response(400, { error: "Invalid input" }));
        await form.submit({ preventDefault() {} });
        assert.equal(ui.notification.error, true);
        assert.equal(ui.title.textContent, `${action} failed`);
        assert.equal(ui.message.textContent, "Invalid input");
        assert.equal(form.button.disabled, false);
    }
    ui.close.click();
    assert.equal(ui.notification.hidden, true);
    assert.deepEqual(ui.refreshes, { users: 4, logs: 4 });
});

test("unexpected responses and network errors do not report success", async () => {
    const ui = setup();
    ui.setFetch(async () => response(200, { message: "Not created" }));
    await ui.create.submit({ preventDefault() {} });
    assert.equal(ui.title.textContent, "Create user failed");
    assert.equal(ui.message.textContent, "Unexpected response from the server.");

    ui.setFetch(async () => { throw new Error("Offline"); });
    await ui.modify.submit({ preventDefault() {} });
    assert.equal(ui.title.textContent, "Modify user failed");
    assert.equal(ui.message.textContent, "Could not contact the server. Please try again.");
    assert.equal(ui.modify.button.disabled, false);
    assert.deepEqual(ui.refreshes, { users: 2, logs: 2 });
});
