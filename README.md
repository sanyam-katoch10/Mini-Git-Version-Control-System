# MiniGit API

A web-based version control system built with **DSA concepts**.

## DSA Concepts Used

| Concept | Usage |
|---|---|
| 🌳 Binary Tree | Commit history (parent → children) |
| 📚 Stack | Undo / Redo operations |
| 🔗 Linked List | Branch tracking |
| 🔑 Hashing | File state identification |
| 🔄 Recursion | History traversal |
| 📦 Array | File storage |
| ↩️ Backtracking | Revert operation (DFS) |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/init` | Initialize repository |
| POST | `/api/add` | Stage a file |
| POST | `/api/commit` | Commit staged files |
| GET | `/api/log` | Commit history |
| GET | `/api/status` | Working tree status |
| POST | `/api/diff` | Compare file with commit |
| POST | `/api/branch` | Create branch |
| POST | `/api/checkout` | Switch branch |
| GET | `/api/branches` | List branches |
| POST | `/api/merge` | Merge branch |
| POST | `/api/undo` | Undo last commit |
| POST | `/api/redo` | Redo undone commit |
| POST | `/api/revert` | Revert to commit |

## Deploy

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
