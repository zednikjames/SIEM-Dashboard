const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function setup(filename, containerId) {
    function element(tag) {
        return {
            tag,
            children: [],
            classList: { add() {} },
            appendChild(child) { this.children.push(child); },
            replaceChildren(fragment) { this.children = [...fragment.children]; },
        };
    }

    const container = element("container");
    const errors = [];
    let fetchHandler = async () => ({ ok: true, json: async () => [] });
    const context = {
        document: {
            getElementById(id) { return id === containerId ? container : null; },
            createElement: element,
            createDocumentFragment() { return element("fragment"); },
        },
        fetch: (...args) => fetchHandler(...args),
        console: { error(...args) { errors.push(args); } },
    };
    const script = fs.readFileSync(
        path.join(__dirname, "..", "src", "static", "js", filename), "utf8",
    );
    vm.runInNewContext(script, context);
    return { context, container, errors, setFetch(handler) { fetchHandler = handler; } };
}

test("user list refresh replaces rows and keeps them on request failure", async () => {
    const ui = setup("user-list.js", "user-list-body");
    await new Promise(setImmediate);
    ui.setFetch(async () => ({
        ok: true, json: async () => [{ full_name: "Alice", email: "a@example.com", role: "Analyst", active: true }],
    }));
    await ui.context.loadUsers();
    assert.equal(ui.container.children.length, 1);
    assert.equal(ui.container.children[0].children[0].textContent, "Alice");
    await ui.context.loadUsers();
    assert.equal(ui.container.children.length, 1);

    ui.setFetch(async () => ({ ok: false, status: 500 }));
    await ui.context.loadUsers();
    assert.equal(ui.container.children.length, 1);
    assert.equal(ui.errors.length, 1);
});

test("audit refresh sorts events and ignores an older in-flight response", async () => {
    const ui = setup("audit-log.js", "audit-log-content");
    await new Promise(setImmediate);
    let resolveOld;
    ui.setFetch(() => new Promise(resolve => { resolveOld = resolve; }));
    const oldRequest = ui.context.loadAuditLogs();
    const events = [
        { action: "older", event_id: "1", timestamp: "2026-01-01T10:00:00Z" },
        { action: "newer", event_id: "2", timestamp: "2026-01-01T11:00:00Z" },
    ];
    ui.setFetch(async () => ({ ok: true, json: async () => events }));
    await ui.context.loadAuditLogs();
    resolveOld({ ok: true, json: async () => [] });
    await oldRequest;
    assert.equal(ui.container.children.length, 2);
    assert.equal(ui.container.children[0].children[0].textContent, "newer - 2");
});
