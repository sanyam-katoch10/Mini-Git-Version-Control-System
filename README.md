# ⎇ MiniGit — Version Control System

A **web-based version control system** that simulates core Git functionality, built from scratch using fundamental **Data Structures & Algorithms**.

<p align="center">
  <a href="https://mini-git-dsa.onrender.com/">
    <img src="https://img.shields.io/badge/🚀_Live_Demo-Render-000000?style=for-the-badge&logo=render&logoColor=white" alt="Live Demo"/>
  </a>
  <br/>
  <a href="https://mini-git-dsa.onrender.com/docs">
    <img src="https://img.shields.io/badge/FastAPI-Docs-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="API Docs"/>
  </a>
</p>

---

## 🎯 Project Highlights

- **Built a fully functional VCS** with branching, merging, undo/redo, and commit history
- **7 core DSA concepts** implemented from scratch — no external libraries for any data structure
- **DAG-based commit history** — same structure real Git uses internally
- **Multi-Repository support** — create, switch, and manage multiple named repositories
- **REST API** with 17 endpoints using FastAPI
- **Interactive terminal UI** that mimics a real Git CLI in the browser
- **Deployable** on Render with zero config + UptimeRobot keepalive

---

## 🧠 Data Structures & Algorithms Used

| DSA Concept | Where It's Used | Implementation |
|---|---|---|
| **DAG (Directed Acyclic Graph)** | Commit history — merge commits connect separate branch histories | `Commit` class with parent/children pointers |
| **Stack** | Undo / Redo operations | Custom `CommitStack` (push, pop, peek) |
| **Linked List** | Branch tracking — branches form a singly linked list | `Branch` nodes with `next` pointer, `BranchList` |
| **Hashing** | File state identification — detect changes between versions | Polynomial rolling hash → 8-char hex string |
| **Recursion** | History traversal — walk commit chain to count/display history | `count_commits()`, `get_history_list()` |
| **Array (List)** | File storage — working directory and staging area | `FileState` with add, remove, get, copy |
| **Backtracking (DFS)** | Revert operation — search entire commit tree to find target | `find_commit()` with depth-first traversal |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                   Frontend                        │
│   index.html  ·  style.css  ·  app.js            │
│   (Terminal UI + Commit Graph + File Explorer)    │
└───────────────────────┬──────────────────────────┘
                        │ fetch() API calls
┌───────────────────────▼──────────────────────────┐
│                  FastAPI Server                   │
│                    main.py                        │
│              (17 REST Endpoints)                  │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│                  Core Engine                      │
│      models.py          storage.py               │
│  (DSA Structures)    (JSON Persistence)           │
└──────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/init` | Initialize repository |
| `POST` | `/api/add` | Stage a file (filename + content) |
| `POST` | `/api/commit` | Commit staged files with message |
| `GET` | `/api/log` | Get full commit history (recursive) |
| `GET` | `/api/status` | Working tree + staging area status |
| `POST` | `/api/diff` | Compare file against last commit |
| `POST` | `/api/branch` | Create a new branch |
| `POST` | `/api/checkout` | Switch to a branch |
| `GET` | `/api/branches` | List all branches |
| `POST` | `/api/merge` | Merge branch into current (source-wins) |
| `POST` | `/api/undo` | Undo last commit (stack pop) |
| `POST` | `/api/redo` | Redo undone commit (stack push) |
| `POST` | `/api/revert` | Revert to specific commit (DFS search) |
| `POST` | `/api/reset` | Reset all repositories |
| `POST` | `/api/repo/create` | Create a new named repository |
| `POST` | `/api/repo/switch` | Switch active repository |
| `GET` | `/api/repos` | List all repositories |
| `DELETE` | `/api/repo/delete` | Delete a repository |
| `GET` | `/health` | Health check (UptimeRobot) |

> Interactive Swagger docs available at `/docs`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Persistence | JSON file storage |
| Deployment | Render |

---

## 🚀 Deployment

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 📂 Project Structure

```
minigit-api/
├── main.py            # FastAPI app — 17 REST endpoints + multi-repo registry
├── models.py          # DSA: DAG, Stack, LinkedList, Hash, Array, Recursion, Backtracking
├── storage.py         # JSON persistence layer
├── requirements.txt   # Python dependencies
├── Procfile           # Deployment start command
└── static/
    ├── index.html     # Terminal UI
    ├── style.css      # Dark theme styling
    └── app.js         # Command parsing + API client
```

---

## 👤 Author

**Sanyam Katoch**  
Built as a DSA project demonstrating practical application of data structures in a real-world system.
