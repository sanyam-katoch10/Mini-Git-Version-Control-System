import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from models import (
    AddRequest, CommitRequest, BranchRequest, CheckoutRequest,
    MergeRequest, RevertRequest, DiffRequest,
    FileState, Commit, CommitStack, BranchList,
    generate_hash, get_timestamp,
    count_commits, find_commit, find_in_history, get_history_list,
)
from storage import load_data, save_data


app = FastAPI(title="MiniGit API", version="1.0")


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}


class MiniGitState:
    def __init__(self):
        self.working_files = FileState()
        self.staging_area = FileState()
        self.branches = BranchList()
        self.undo_stack = CommitStack()
        self.redo_stack = CommitStack()
        self.root_commit = None
        self.initialized = False

git = MiniGitState()



@app.post("/api/init")
def init_repo():
    if git.initialized:
        return {"success": False, "message": "Repository already initialized."}
    git.branches.add_branch("main", None)
    git.initialized = True
    return {
        "success": True,
        "message": "Initialized empty MiniGit repository.",
        "branch": "main",
    }


@app.post("/api/add")
def add_file(req: AddRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized. Run 'init' first."}

    git.staging_area.add_file(req.filename, req.content)
    git.working_files.add_file(req.filename, req.content)
    h = generate_hash(req.content)

    return {
        "success": True,
        "message": f"Staged: {req.filename}",
        "hash": h,
        "filename": req.filename,
    }


@app.post("/api/commit")
def commit_files(req: CommitRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    if git.staging_area.file_count == 0:
        return {"success": False, "message": "Nothing to commit. Use 'add' first."}

    ts = get_timestamp()
    raw = req.message + ts
    for f in git.staging_area.files:
        raw += f.content
    commit_id = generate_hash(raw)

    new_commit = Commit(commit_id, req.message)
    new_commit.snapshot = git.staging_area.copy()

    current = git.branches.active
    if current.head is not None:
        new_commit.parent = current.head
        current.head.children.append(new_commit)

    if git.root_commit is None:
        git.root_commit = new_commit

    current.head = new_commit
    git.undo_stack.push(new_commit)
    git.redo_stack.clear()
    git.staging_area = FileState()

    save_data(get_history_list(current.head))

    return {
        "success": True,
        "message": f"[{current.name} {commit_id}] {req.message}",
        "commitId": commit_id,
        "branch": current.name,
        "fileCount": new_commit.snapshot.file_count,
    }


@app.get("/api/log")
def get_log():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    current = git.branches.active
    if current.head is None:
        return {"success": True, "message": "No commits yet.", "commits": [], "total": 0}

    commits = get_history_list(current.head)
    return {
        "success": True,
        "message": f"Commit History ({current.name})",
        "branch": current.name,
        "commits": commits,
        "total": count_commits(current.head),
    }


@app.get("/api/status")
def get_status():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    staged = [
        {"name": f.name, "hash": generate_hash(f.content)}
        for f in git.staging_area.files
    ]
    working = [
        {"name": f.name, "hash": generate_hash(f.content)}
        for f in git.working_files.files
    ]

    return {
        "success": True,
        "branch": git.branches.active.name,
        "staged": staged,
        "working": working,
        "undoCount": git.undo_stack.size(),
        "redoCount": git.redo_stack.size(),
    }


@app.post("/api/diff")
def diff_file(req: DiffRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    current = git.branches.active
    work_file = git.working_files.get_file(req.filename)
    if work_file is None:
        return {"success": False, "message": f"File '{req.filename}' not in working directory."}

    work_hash = generate_hash(work_file.content)

    if current.head is None:
        return {
            "success": True,
            "status": "new",
            "message": f"+ {req.filename} [{work_hash}] (new file)",
            "filename": req.filename,
            "workingHash": work_hash,
            "workingContent": work_file.content,
        }

    commit_file = current.head.snapshot.get_file(req.filename)
    if commit_file is None:
        return {
            "success": True,
            "status": "new",
            "message": f"+ {req.filename} (new — not in last commit)",
            "filename": req.filename,
            "workingHash": work_hash,
            "workingContent": work_file.content,
        }

    commit_hash = generate_hash(commit_file.content)

    if work_hash == commit_hash:
        return {
            "success": True,
            "status": "unchanged",
            "message": f"{req.filename} — no changes.",
            "filename": req.filename,
        }

    return {
        "success": True,
        "status": "modified",
        "message": f"{req.filename} — MODIFIED",
        "filename": req.filename,
        "committedHash": commit_hash,
        "workingHash": work_hash,
        "committedContent": commit_file.content,
        "workingContent": work_file.content,
    }


@app.post("/api/branch")
def create_branch(req: BranchRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    if git.branches.find_branch(req.name) is not None:
        return {"success": False, "message": f"Branch '{req.name}' already exists."}

    head = git.branches.active.head
    git.branches.add_branch(req.name, head)
    return {"success": True, "message": f"Created branch: {req.name}", "branch": req.name}


@app.post("/api/checkout")
def checkout_branch(req: CheckoutRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    if git.branches.switch_branch(req.name):
        b = git.branches.active
        if b.head is not None:
            git.working_files = b.head.snapshot.copy()
            msg = f"Switched to branch: {req.name} — Restored {git.working_files.file_count} file(s)."
        else:
            git.working_files = FileState()
            msg = f"Switched to branch: {req.name} — Branch has no commits yet."
        git.staging_area = FileState()
        return {"success": True, "message": msg, "branch": req.name}

    return {"success": False, "message": f"Branch '{req.name}' not found."}


@app.get("/api/branches")
def list_branches():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    return {
        "success": True,
        "branches": git.branches.to_list(),
        "total": git.branches.count(),
    }


@app.post("/api/merge")
def merge_branch(req: MergeRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    src = git.branches.find_branch(req.branch)
    if src is None:
        return {"success": False, "message": f"Branch '{req.branch}' not found."}
    if src == git.branches.active:
        return {"success": False, "message": "Cannot merge branch into itself."}
    if src.head is None:
        return {"success": False, "message": "Source branch has no commits."}

    ts = get_timestamp()
    raw = "merge:" + req.branch + ts
    commit_id = generate_hash(raw)
    msg = f"Merge branch '{req.branch}' into {git.branches.active.name}"

    merge_commit = Commit(commit_id, msg)

    if git.branches.active.head is not None:
        merge_commit.snapshot = git.branches.active.head.snapshot.copy()

    for f in src.head.snapshot.files:
        if merge_commit.snapshot.get_file(f.name) is None:
            merge_commit.snapshot.add_file(f.name, f.content)

    merge_commit.parent = git.branches.active.head
    if git.branches.active.head is not None:
        git.branches.active.head.children.append(merge_commit)

    git.branches.active.head = merge_commit
    git.working_files = merge_commit.snapshot.copy()
    git.undo_stack.push(merge_commit)
    git.redo_stack.clear()

    save_data(get_history_list(git.branches.active.head))

    return {
        "success": True,
        "message": msg,
        "commitId": commit_id,
        "fileCount": merge_commit.snapshot.file_count,
    }


@app.post("/api/undo")
def undo():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    if git.undo_stack.is_empty():
        return {"success": False, "message": "Nothing to undo."}

    c = git.undo_stack.pop()
    git.redo_stack.push(c)

    if c.parent is not None:
        git.branches.active.head = c.parent
        git.working_files = c.parent.snapshot.copy()
        return {
            "success": True,
            "message": f"Undo: reverted to commit {c.parent.commit_id}",
            "commitId": c.parent.commit_id,
        }
    else:
        git.branches.active.head = None
        git.working_files = FileState()
        return {
            "success": True,
            "message": "Undo: reverted to initial state (no commits).",
        }


@app.post("/api/redo")
def redo():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    if git.redo_stack.is_empty():
        return {"success": False, "message": "Nothing to redo."}

    c = git.redo_stack.pop()
    git.undo_stack.push(c)

    git.branches.active.head = c
    git.working_files = c.snapshot.copy()
    return {
        "success": True,
        "message": f"Redo: restored commit {c.commit_id} — {c.message}",
        "commitId": c.commit_id,
    }


@app.post("/api/revert")
def revert(req: RevertRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}

    current = git.branches.active
    if current.head is None:
        return {"success": False, "message": "No commits to revert."}

    target = find_in_history(current.head, req.commit_id)
    if target is None and git.root_commit is not None:
        target = find_commit(git.root_commit, req.commit_id)

    if target is None:
        return {"success": False, "message": f"Commit '{req.commit_id}' not found."}

    git.working_files = target.snapshot.copy()
    git.staging_area = target.snapshot.copy()

    ts = get_timestamp()
    new_id = generate_hash("revert:" + req.commit_id + ts)
    msg = f"Revert to {req.commit_id}"

    revert_commit = Commit(new_id, msg)
    revert_commit.snapshot = target.snapshot.copy()
    revert_commit.parent = current.head
    current.head.children.append(revert_commit)
    current.head = revert_commit

    git.undo_stack.push(revert_commit)
    git.redo_stack.clear()

    save_data(get_history_list(current.head))

    return {
        "success": True,
        "message": f"Reverted to commit {req.commit_id}",
        "newCommitId": new_id,
        "fileCount": git.working_files.file_count,
    }


@app.post("/api/reset")
def reset_repo():
    global git
    git = MiniGitState()
    save_data([])
    return {"success": True, "message": "Repository reset."}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


handler = app


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
