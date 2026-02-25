from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime


# ── Pydantic Request/Response Models ──────────────────────────────────

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


# ── DSA Core Data Structures ─────────────────────────────────────────

class File:
    """Simple file representation (name + content)."""
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

    def to_dict(self):
        return {"name": self.name, "content": self.content}


class FileState:
    """Array-based file storage (mirrors C++ fixed-size array approach)."""
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


# ── Hashing ───────────────────────────────────────────────────────────

def generate_hash(data: str) -> str:
    """Custom hash function (port of C++ version — polynomial rolling hash)."""
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


# ── Commit Tree Node ─────────────────────────────────────────────────

class Commit:
    """Tree node — each commit points to parent + children (branching)."""
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


# ── Stack (Undo / Redo) ──────────────────────────────────────────────

class CommitStack:
    """Custom stack implementation for undo/redo operations."""
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


# ── Branch (Linked List Node) ────────────────────────────────────────

class Branch:
    """Linked list node — each branch has a name, head commit, and next pointer."""
    def __init__(self, name: str, head: Optional[Commit] = None):
        self.name = name
        self.head = head
        self.next: Optional["Branch"] = None


class BranchList:
    """Linked list of branches with an active branch pointer."""
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


# ── Recursive / Backtracking Helpers ─────────────────────────────────

def count_commits(node: Optional[Commit]) -> int:
    """Recursion — walk parent chain to count depth."""
    if node is None:
        return 0
    return 1 + count_commits(node.parent)


def find_commit(root: Optional[Commit], commit_id: str) -> Optional[Commit]:
    """Backtracking DFS — search entire commit tree."""
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
    """Recursion — walk parent chain to find a specific commit."""
    if node is None:
        return None
    if node.commit_id == commit_id:
        return node
    return find_in_history(node.parent, commit_id)


def get_history_list(node: Optional[Commit]) -> List[Dict]:
    """Recursion — collect commit history as a list (newest first)."""
    if node is None:
        return []
    result = [node.to_dict()]
    result.extend(get_history_list(node.parent))
    return result
