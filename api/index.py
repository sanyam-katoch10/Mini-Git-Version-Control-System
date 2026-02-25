from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime
from fastapi import FastAPI


class AddRequest(BaseModel):
    filename: str
    content: str

class CommitRequest(BaseModel):
    message: str

class BranchRequest(BaseModel):
    name: str

class CheckoutRequest(BaseModel):
    name: str

class MergeRequest(BaseModel):
    branch: str

class RevertRequest(BaseModel):
    commit_id: str

class DiffRequest(BaseModel):
    filename: str


class File:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

    def to_dict(self):
        return {"name": self.name, "content": self.content}


class FileState:
    def __init__(self):
        self.files: List[File] = []

    @property
    def file_count(self):
        return len(self.files)

    def add_file(self, name: str, content: str):
        for f in self.files:
            if f.name == name:
                f.content = content
                return
        self.files.append(File(name, content))

    def remove_file(self, name: str):
        self.files = [f for f in self.files if f.name != name]

    def get_file(self, name: str) -> Optional[File]:
        for f in self.files:
            if f.name == name:
                return f
        return None

    def copy(self) -> "FileState":
        fs = FileState()
        for f in self.files:
            fs.files.append(File(f.name, f.content))
        return fs

    def to_dict(self):
        return [f.to_dict() for f in self.files]


def generate_hash(data: str) -> str:
    h = 0
    for ch in data:
        h = h * 31 + ord(ch)
    if h < 0:
        h = -h
    h = h & 0xFFFFFFFF
    hex_chars = "0123456789abcdef"
    result = ""
    temp = h
    for _ in range(8):
        result = hex_chars[temp % 16] + result
        temp //= 16
    return result


def get_timestamp() -> str:
    return datetime.now().strftime("%a %b %d %H:%M:%S %Y")


class Commit:
    def __init__(self, commit_id: str, message: str):
        self.commit_id = commit_id
        self.message = message
        self.timestamp = get_timestamp()
        self.parent: Optional["Commit"] = None
        self.children: List["Commit"] = []
        self.snapshot = FileState()

    def to_dict(self):
        return {
            "id": self.commit_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "parent": self.parent.commit_id if self.parent else None,
            "children": [c.commit_id for c in self.children],
            "files": self.snapshot.to_dict(),
            "fileCount": self.snapshot.file_count,
        }


class CommitStack:
    def __init__(self):
        self._data: List[Commit] = []

    def push(self, commit: Commit):
        self._data.append(commit)

    def pop(self) -> Optional[Commit]:
        if self._data:
            return self._data.pop()
        return None

    def peek(self) -> Optional[Commit]:
        if self._data:
            return self._data[-1]
        return None

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def size(self) -> int:
        return len(self._data)

    def clear(self):
        self._data.clear()


class Branch:
    def __init__(self, name: str, head: Optional[Commit] = None):
        self.name = name
        self.head = head
        self.next: Optional["Branch"] = None


class BranchList:
    def __init__(self):
        self.first: Optional[Branch] = None
        self.active: Optional[Branch] = None

    def add_branch(self, name: str, head: Optional[Commit] = None):
        new_branch = Branch(name, head)
        if self.first is None:
            self.first = new_branch
        else:
            curr = self.first
            while curr.next is not None:
                curr = curr.next
            curr.next = new_branch
        if self.active is None:
            self.active = new_branch

    def find_branch(self, name: str) -> Optional[Branch]:
        curr = self.first
        while curr is not None:
            if curr.name == name:
                return curr
            curr = curr.next
        return None

    def switch_branch(self, name: str) -> bool:
        b = self.find_branch(name)
        if b is not None:
            self.active = b
            return True
        return False

    def delete_branch(self, name: str) -> bool:
        if self.active and self.active.name == name:
            return False
        if self.first is None:
            return False
        if self.first.name == name:
            self.first = self.first.next
            return True
        curr = self.first
        while curr.next is not None:
            if curr.next.name == name:
                curr.next = curr.next.next
                return True
            curr = curr.next
        return False

    def count(self) -> int:
        c = 0
        curr = self.first
        while curr is not None:
            c += 1
            curr = curr.next
        return c

    def to_list(self) -> List[Dict]:
        result = []
        curr = self.first
        while curr is not None:
            result.append({
                "name": curr.name,
                "active": curr == self.active,
                "head": curr.head.commit_id if curr.head else None,
            })
            curr = curr.next
        return result


def count_commits(node: Optional[Commit]) -> int:
    if node is None:
        return 0
    return 1 + count_commits(node.parent)


def find_commit(root: Optional[Commit], commit_id: str) -> Optional[Commit]:
    if root is None:
        return None
    if root.commit_id == commit_id:
        return root
    for child in root.children:
        result = find_commit(child, commit_id)
        if result is not None:
            return result
    return None


def find_in_history(node: Optional[Commit], commit_id: str) -> Optional[Commit]:
    if node is None:
        return None
    if node.commit_id == commit_id:
        return node
    return find_in_history(node.parent, commit_id)


def get_history_list(node: Optional[Commit]) -> List[Dict]:
    if node is None:
        return []
    result = [node.to_dict()]
    result.extend(get_history_list(node.parent))
    return result


app = FastAPI(title="MiniGit API", version="1.0")


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
    return {"success": True, "message": "Initialized empty MiniGit repository.", "branch": "main"}


@app.post("/api/add")
def add_file(req: AddRequest):
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized. Run 'init' first."}
    git.staging_area.add_file(req.filename, req.content)
    git.working_files.add_file(req.filename, req.content)
    h = generate_hash(req.content)
    return {"success": True, "message": f"Staged: {req.filename}", "hash": h, "filename": req.filename}


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
    return {
        "success": True,
        "message": f"[{current.name} {commit_id}] {req.message}",
        "commitId": commit_id, "branch": current.name,
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
        "success": True, "message": f"Commit History ({current.name})",
        "branch": current.name, "commits": commits,
        "total": count_commits(current.head),
    }


@app.get("/api/status")
def get_status():
    if not git.initialized:
        return {"success": False, "message": "Error: repo not initialized."}
    staged = [{"name": f.name, "hash": generate_hash(f.content)} for f in git.staging_area.files]
    working = [{"name": f.name, "hash": generate_hash(f.content)} for f in git.working_files.files]
    return {
        "success": True, "branch": git.branches.active.name,
        "staged": staged, "working": working,
        "undoCount": git.undo_stack.size(), "redoCount": git.redo_stack.size(),
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
        return {"success": True, "status": "new", "message": f"+ {req.filename} [{work_hash}] (new file)",
                "filename": req.filename, "workingHash": work_hash, "workingContent": work_file.content}
    commit_file = current.head.snapshot.get_file(req.filename)
    if commit_file is None:
        return {"success": True, "status": "new", "message": f"+ {req.filename} (new)",
                "filename": req.filename, "workingHash": work_hash, "workingContent": work_file.content}
    commit_hash = generate_hash(commit_file.content)
    if work_hash == commit_hash:
        return {"success": True, "status": "unchanged", "message": f"{req.filename} — no changes.", "filename": req.filename}
    return {
        "success": True, "status": "modified", "message": f"{req.filename} — MODIFIED",
        "filename": req.filename, "committedHash": commit_hash, "workingHash": work_hash,
        "committedContent": commit_file.content, "workingContent": work_file.content,
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
    return {"success": True, "branches": git.branches.to_list(), "total": git.branches.count()}


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
    commit_id = generate_hash("merge:" + req.branch + ts)
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
    return {"success": True, "message": msg, "commitId": commit_id, "fileCount": merge_commit.snapshot.file_count}


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
        return {"success": True, "message": f"Undo: reverted to commit {c.parent.commit_id}", "commitId": c.parent.commit_id}
    else:
        git.branches.active.head = None
        git.working_files = FileState()
        return {"success": True, "message": "Undo: reverted to initial state (no commits)."}


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
    return {"success": True, "message": f"Redo: restored commit {c.commit_id} — {c.message}", "commitId": c.commit_id}


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
    return {"success": True, "message": f"Reverted to commit {req.commit_id}", "newCommitId": new_id, "fileCount": git.working_files.file_count}


@app.post("/api/reset")
def reset_repo():
    global git
    git = MiniGitState()
    return {"success": True, "message": "Repository reset."}
