const API = "/api";
const terminal = document.getElementById("terminal");
const input = document.getElementById("input");
const clearBtn = document.getElementById("clearBtn");
const promptBranch = document.getElementById("promptBranch");

let history = [];
let histIdx = -1;

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
        const cmd = input.value.trim();
        history.push(cmd);
        histIdx = history.length;
        printLine("minigit❯ " + cmd, "cmd");
        handleCommand(cmd);
        input.value = "";
    }
    if (e.key === "ArrowUp") {
        e.preventDefault();
        if (histIdx > 0) { histIdx--; input.value = history[histIdx]; }
    }
    if (e.key === "ArrowDown") {
        e.preventDefault();
        if (histIdx < history.length - 1) { histIdx++; input.value = history[histIdx]; }
        else { histIdx = history.length; input.value = ""; }
    }
});

clearBtn.addEventListener("click", () => {
    terminal.innerHTML = "";
});

function run(cmd) {
    input.value = cmd;
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
}

function printLine(text, cls = "info") {
    const div = document.createElement("div");
    div.className = "output-line " + cls;
    div.textContent = text;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function printLines(lines, cls = "info") {
    lines.forEach((l) => printLine(l, cls));
}

async function api(method, endpoint, body = null) {
    try {
        const opts = { method, headers: { "Content-Type": "application/json" } };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(API + endpoint, opts);
        return await res.json();
    } catch (err) {
        return { success: false, message: "Connection error: " + err.message };
    }
}

async function handleCommand(raw) {
    const parts = raw.split(" ");
    const cmd = parts[0].toLowerCase();

    switch (cmd) {
        case "help":
            printLines([
                "",
                "=== MiniGit Commands ===",
                "  init                    Initialize repository",
                "  add <file> <content>    Stage a file",
                "  commit <message>        Commit staged files",
                "  log                     Show commit history",
                "  status                  Show working tree status",
                "  diff <file>             Compare file with last commit",
                "  branch <name>           Create a new branch",
                "  checkout <name>         Switch to a branch",
                "  branches                List all branches",
                "  merge <branch>          Merge branch into current",
                "  undo                    Undo last commit",
                "  redo                    Redo undone commit",
                "  revert <commit-id>      Revert to a specific commit",
                "  clear                   Clear terminal",
                "  help                    Show this help",
                "",
            ]);
            break;

        case "clear":
            terminal.innerHTML = "";
            break;

        case "init": {
            const r = await api("POST", "/init");
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "add": {
            const filename = parts[1];
            const content = parts.slice(2).join(" ") || "(empty file)";
            if (!filename) { printLine("Usage: add <filename> <content>", "error"); break; }
            const r = await api("POST", "/add", { filename, content });
            printLine(r.message + (r.hash ? "  [hash: " + r.hash + "]" : ""), r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "commit": {
            const message = parts.slice(1).join(" ");
            if (!message) { printLine("Usage: commit <message>", "error"); break; }
            const r = await api("POST", "/commit", { message });
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) {
                printLine(r.fileCount + " file(s) committed.", "info");
                refreshAll();
            }
            break;
        }

        case "log": {
            const r = await api("GET", "/log");
            if (!r.success) { printLine(r.message, "error"); break; }
            if (!r.commits || r.commits.length === 0) { printLine("No commits yet.", "info"); break; }
            printLine("=== Commit History (" + r.branch + ") ===", "success");
            r.commits.forEach((c) => {
                printLine("");
                printLine("  commit " + c.id, "success");
                printLine("  Date:   " + c.timestamp, "info");
                printLine("  Msg:    " + c.message, "info");
                printLine("  Files:  " + c.fileCount, "info");
            });
            printLine("");
            printLine("Total: " + r.total + " commit(s)", "info");
            break;
        }

        case "status": {
            const r = await api("GET", "/status");
            if (!r.success) { printLine(r.message, "error"); break; }
            printLine("On branch: " + r.branch, "success");
            if (r.staged.length > 0) {
                printLine("\nStaged files:", "info");
                r.staged.forEach((f) => printLine("  + " + f.name, "success"));
            }
            printLine("\nWorking directory:", "info");
            if (r.working.length === 0) {
                printLine("  (empty)", "info");
            } else {
                r.working.forEach((f) => printLine("  " + f.name + "  [" + f.hash + "]", "info"));
            }
            printLine("\nUndo stack: " + r.undoCount + " | Redo stack: " + r.redoCount, "info");
            break;
        }

        case "diff": {
            const filename = parts[1];
            if (!filename) { printLine("Usage: diff <filename>", "error"); break; }
            const r = await api("POST", "/diff", { filename });
            printLine(r.message, r.success ? (r.status === "modified" ? "error" : "success") : "error");
            if (r.committedContent !== undefined) {
                printLine("\n--- committed ---", "info");
                printLine(r.committedContent, "info");
                printLine("--- working ---", "info");
                printLine(r.workingContent, "info");
            }
            break;
        }

        case "branch": {
            const name = parts[1];
            if (!name) { printLine("Usage: branch <name>", "error"); break; }
            const r = await api("POST", "/branch", { name });
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "checkout": {
            const name = parts[1];
            if (!name) { printLine("Usage: checkout <name>", "error"); break; }
            const r = await api("POST", "/checkout", { name });
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "branches": {
            const r = await api("GET", "/branches");
            if (!r.success) { printLine(r.message, "error"); break; }
            printLine("=== Branches ===", "success");
            r.branches.forEach((b) => {
                printLine(b.active ? "  * " + b.name + " (active)" : "    " + b.name, b.active ? "success" : "info");
            });
            printLine("Total: " + r.total + " branch(es)", "info");
            break;
        }

        case "merge": {
            const branch = parts[1];
            if (!branch) { printLine("Usage: merge <branch>", "error"); break; }
            const r = await api("POST", "/merge", { branch });
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) {
                printLine("[" + r.commitId + "] " + r.fileCount + " file(s)", "info");
                refreshAll();
            }
            break;
        }

        case "undo": {
            const r = await api("POST", "/undo");
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "redo": {
            const r = await api("POST", "/redo");
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) refreshAll();
            break;
        }

        case "revert": {
            const commitId = parts[1];
            if (!commitId) { printLine("Usage: revert <commit-id>", "error"); break; }
            const r = await api("POST", "/revert", { commit_id: commitId });
            printLine(r.message, r.success ? "success" : "error");
            if (r.success) {
                printLine("New commit: [" + r.newCommitId + "]  " + r.fileCount + " file(s)", "info");
                refreshAll();
            }
            break;
        }

        default:
            printLine("Unknown command: " + cmd + ". Type 'help' for options.", "error");
    }
}

async function refreshAll() {
    await Promise.all([refreshBranches(), refreshStatus(), refreshLog()]);
}

async function refreshBranches() {
    const r = await api("GET", "/branches");
    const el = document.getElementById("branchList");
    if (!r.success || !r.branches) { el.innerHTML = '<li class="muted">No branches</li>'; return; }
    el.innerHTML = r.branches.map((b) =>
        `<li class="${b.active ? "active" : ""}">${b.active ? "● " : "  "}${b.name}</li>`
    ).join("");
    const active = r.branches.find((b) => b.active);
    if (active) promptBranch.textContent = active.name;
}

async function refreshStatus() {
    const r = await api("GET", "/status");
    if (!r.success) return;
    document.getElementById("sBranch").textContent = r.branch;
    document.getElementById("sStaged").textContent = r.staged.length;
    document.getElementById("sFiles").textContent = r.working.length;
    document.getElementById("sUndo").textContent = r.undoCount;
    document.getElementById("sRedo").textContent = r.redoCount;

    const fl = document.getElementById("fileList");
    if (r.working.length === 0) {
        fl.innerHTML = '<p class="muted">No files</p>';
    } else {
        fl.innerHTML = r.working.map((f) =>
            `<div class="file-item"><span>📄 ${f.name}</span><span class="file-hash">${f.hash}</span></div>`
        ).join("");
    }
}

async function refreshLog() {
    const r = await api("GET", "/log");
    const el = document.getElementById("commitGraph");
    if (!r.success || !r.commits || r.commits.length === 0) {
        el.innerHTML = '<p class="muted">No commits yet</p>';
        return;
    }
    el.innerHTML = r.commits.map((c) =>
        `<div class="commit-node">
            <div>
                <span class="commit-id">${c.id}</span><br>
                <span class="commit-msg">${c.message}</span><br>
                <span class="commit-time">${c.timestamp}</span>
            </div>
        </div>`
    ).join("");
}

input.focus();
