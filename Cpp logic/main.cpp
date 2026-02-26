#include <iostream>
#include <sstream>
#include <string>
#include "minigit.h"
using namespace std;

class MiniGit {
private:
    FileState    workingFiles;
    FileState    stagingArea;
    BranchList   branches;
    CommitStack  undoStack;
    CommitStack  redoStack;
    Commit*      rootCommit;
    bool         initialized;

public:
    MiniGit() : rootCommit(NULL), initialized(false) {}

    void init() {
        if (initialized) {
            cout << "  Repository already initialized." << endl;
            return;
        }
        branches.addBranch("main", NULL);
        initialized = true;
        cout << "  Initialized empty MiniGit repository." << endl;
        cout << "  Branch: main (active)" << endl;
    }

    void add(string filename, string content) {
        if (!initialized) { cout << "  Error: repo not initialized. Run 'init' first." << endl; return; }

        stagingArea.addFile(filename, content);
        workingFiles.addFile(filename, content);

        string hash = generateHash(content);
        cout << "  Staged: " << filename << "  [hash: " << hash << "]" << endl;
    }

    void commit(string message) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        if (stagingArea.fileCount == 0) {
            cout << "  Nothing to commit. Use 'add' first." << endl;
            return;
        }

        string ts = getTimestamp();
        string raw = message + ts;
        for (int i = 0; i < stagingArea.fileCount; i++) {
            raw += stagingArea.files[i].content;
        }
        string id = generateHash(raw);

        Commit* newCommit = new Commit(id, message);
        newCommit->snapshot = stagingArea.copy();

        Branch* current = branches.active;
        if (current->head != NULL) {
            newCommit->parent = current->head;
            if (current->head->childCount < 10) {
                current->head->children[current->head->childCount++] = newCommit;
            }
        }

        if (rootCommit == NULL) {
            rootCommit = newCommit;
        }

        current->head = newCommit;

        undoStack.push(newCommit);
        redoStack.clear();

        stagingArea = FileState();

        cout << "  [" << current->name << " " << id << "] " << message << endl;
        cout << "  " << newCommit->snapshot.fileCount << " file(s) committed." << endl;
    }

    void log() {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        Branch* current = branches.active;
        if (current->head == NULL) {
            cout << "  No commits yet." << endl;
            return;
        }
        cout << "  === Commit History (" << current->name << ") ===" << endl << endl;
        printHistory(current->head);
        cout << "  Total: " << countCommits(current->head) << " commit(s)" << endl;
    }

    void status() {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        cout << "  On branch: " << branches.active->name << endl;

        if (stagingArea.fileCount > 0) {
            cout << "\n  Staged files:" << endl;
            for (int i = 0; i < stagingArea.fileCount; i++) {
                cout << "    + " << stagingArea.files[i].name << endl;
            }
        }

        cout << "\n  Working directory:" << endl;
        if (workingFiles.fileCount == 0) {
            cout << "    (empty)" << endl;
        } else {
            for (int i = 0; i < workingFiles.fileCount; i++) {
                string hash = generateHash(workingFiles.files[i].content);
                cout << "    " << workingFiles.files[i].name << "  [" << hash << "]" << endl;
            }
        }

        cout << "\n  Undo stack: " << undoStack.size() << " operation(s)" << endl;
        cout << "  Redo stack: " << redoStack.size() << " operation(s)" << endl;
    }

    void branch(string name) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        if (branches.findBranch(name) != NULL) {
            cout << "  Branch '" << name << "' already exists." << endl;
            return;
        }

        Commit* head = branches.active->head;
        branches.addBranch(name, head);
        cout << "  Created branch: " << name << endl;
    }

    void checkout(string name) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        if (branches.switchBranch(name)) {
            cout << "  Switched to branch: " << name << endl;

            Branch* b = branches.active;
            if (b->head != NULL) {
                workingFiles = b->head->snapshot.copy();
                cout << "  Restored " << workingFiles.fileCount << " file(s)." << endl;
            } else {
                workingFiles = FileState();
                cout << "  Branch has no commits yet." << endl;
            }
            stagingArea = FileState();
        } else {
            cout << "  Branch '" << name << "' not found." << endl;
        }
    }

    void listBranches() {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        cout << "  === Branches ===" << endl;
        branches.printBranches();
        cout << "  Total: " << branches.count() << " branch(es)" << endl;
    }

    void merge(string branchName) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        Branch* src = branches.findBranch(branchName);
        if (src == NULL) { cout << "  Branch '" << branchName << "' not found." << endl; return; }
        if (src == branches.active) { cout << "  Cannot merge branch into itself." << endl; return; }
        if (src->head == NULL) { cout << "  Source branch has no commits." << endl; return; }

        string ts = getTimestamp();
        string raw = "merge:" + branchName + ts;
        string id = generateHash(raw);
        string msg = "Merge branch '" + branchName + "' into " + branches.active->name;

        Commit* mergeCommit = new Commit(id, msg);

        if (branches.active->head != NULL) {
            mergeCommit->snapshot = branches.active->head->snapshot.copy();
        }

        for (int i = 0; i < src->head->snapshot.fileCount; i++) {
            File* srcFile = &src->head->snapshot.files[i];
            mergeCommit->snapshot.addFile(srcFile->name, srcFile->content);
        }

        mergeCommit->parent = branches.active->head;
        if (branches.active->head != NULL && branches.active->head->childCount < 10) {
            branches.active->head->children[branches.active->head->childCount++] = mergeCommit;
        }

        if (rootCommit == NULL) rootCommit = mergeCommit;

        branches.active->head = mergeCommit;
        workingFiles = mergeCommit->snapshot.copy();
        stagingArea = FileState();

        undoStack.push(mergeCommit);
        redoStack.clear();

        cout << "  " << msg << endl;
        cout << "  [" << id << "] " << mergeCommit->snapshot.fileCount << " file(s)" << endl;
    }

    void undo() {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        if (undoStack.isEmpty()) {
            cout << "  Nothing to undo." << endl;
            return;
        }

        Commit* c = undoStack.pop();
        redoStack.push(c);

        if (c->parent != NULL) {
            branches.active->head = c->parent;
            workingFiles = c->parent->snapshot.copy();
            cout << "  Undo: reverted to commit " << c->parent->commitId << endl;
        } else {
            branches.active->head = NULL;
            workingFiles = FileState();
            cout << "  Undo: reverted to initial state (no commits)." << endl;
        }
    }

    void redo() {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        if (redoStack.isEmpty()) {
            cout << "  Nothing to redo." << endl;
            return;
        }

        Commit* c = redoStack.pop();
        undoStack.push(c);

        branches.active->head = c;
        workingFiles = c->snapshot.copy();
        cout << "  Redo: restored commit " << c->commitId << " — " << c->message << endl;
    }

    void revert(string commitId) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        Branch* current = branches.active;
        if (current->head == NULL) {
            cout << "  No commits to revert." << endl;
            return;
        }

        Commit* target = findInHistory(current->head, commitId);
        if (target == NULL && rootCommit != NULL) {
            target = findCommit(rootCommit, commitId);
        }

        if (target == NULL) {
            cout << "  Commit '" << commitId << "' not found." << endl;
            return;
        }

        workingFiles = target->snapshot.copy();
        stagingArea = target->snapshot.copy();

        string ts = getTimestamp();
        string id = generateHash("revert:" + commitId + ts);
        string msg = "Revert to " + commitId;

        Commit* revertCommit = new Commit(id, msg);
        revertCommit->snapshot = target->snapshot.copy();
        revertCommit->parent = current->head;
        if (current->head->childCount < 10) {
            current->head->children[current->head->childCount++] = revertCommit;
        }
        current->head = revertCommit;

        undoStack.push(revertCommit);
        redoStack.clear();

        cout << "  Reverted to commit " << commitId << endl;
        cout << "  Created revert commit [" << id << "]" << endl;
        cout << "  " << workingFiles.fileCount << " file(s) restored." << endl;
    }

    void diff(string filename) {
        if (!initialized) { cout << "  Error: repo not initialized." << endl; return; }
        Branch* current = branches.active;

        File* workFile = workingFiles.getFile(filename);
        if (workFile == NULL) {
            cout << "  File '" << filename << "' not in working directory." << endl;
            return;
        }

        string workHash = generateHash(workFile->content);

        if (current->head == NULL) {
            cout << "  No commits to compare against." << endl;
            cout << "  + " << filename << " [" << workHash << "] (new file)" << endl;
            return;
        }

        File* commitFile = current->head->snapshot.getFile(filename);
        if (commitFile == NULL) {
            cout << "  + " << filename << " (new — not in last commit)" << endl;
            return;
        }

        string commitHash = generateHash(commitFile->content);

        if (workHash == commitHash) {
            cout << "  " << filename << " — no changes." << endl;
        } else {
            cout << "  " << filename << " — MODIFIED" << endl;
            cout << "  Last commit: [" << commitHash << "]" << endl;
            cout << "  Working:     [" << workHash << "]" << endl;
            cout << "\n  --- committed version ---" << endl;
            cout << "  " << commitFile->content << endl;
            cout << "  --- working version ---" << endl;
            cout << "  " << workFile->content << endl;
        }
    }

    void help() {
        cout << endl;
        cout << "  === MiniGit Commands ===" << endl;
        cout << "  repo create <name>      Create a new repository" << endl;
        cout << "  init                    Initialize repository" << endl;
        cout << "  add <file> <content>    Stage a file" << endl;
        cout << "  commit <message>        Commit staged files" << endl;
        cout << "  log                     Show commit history (recursive)" << endl;
        cout << "  repo switch <name>      Switch to a repository" << endl;
        cout << "  repos                   List all repositories" << endl;
        cout << "  status                  Show working tree status" << endl;
        cout << "  diff <file>             Compare file with last commit" << endl;
        cout << "  branch <name>           Create a new branch" << endl;
        cout << "  checkout <name>         Switch to a branch" << endl;
        cout << "  branches                List all branches" << endl;
        cout << "  merge <branch>          Merge branch into current" << endl;
        cout << "  undo                    Undo last commit" << endl;
        cout << "  redo                    Redo undone commit" << endl;
        cout << "  revert <commit-id>      Revert to a specific commit" << endl;
        cout << "  repo delete <name>      Delete a repository" << endl;
        cout << "  help                    Show this help" << endl;
        cout << "  exit                    Quit MiniGit" << endl;
        cout << endl;
    }
};

int main() {
    MiniGit* repos[20];
    string repoNames[20];
    int repoCount = 0;
    int activeRepo = -1;

    cout << endl;
    cout << "  ╔═══════════════════════════════════════╗" << endl;
    cout << "  ║          M I N I   G I T              ║" << endl;
    cout << "  ║     Version Control System v1.0       ║" << endl;
    cout << "  ║                                       ║" << endl;
    cout << "  ║  DSA: Tree | Stack | LinkedList       ║" << endl;
    cout << "  ║       Hash | Recursion | Array        ║" << endl;
    cout << "  ║       Backtracking                    ║" << endl;
    cout << "  ╚═══════════════════════════════════════╝" << endl;
    cout << endl;
    cout << "  Type 'help' for commands." << endl;
    cout << endl;

    string line;
    while (true) {
        if (activeRepo >= 0)
            cout << "  " << repoNames[activeRepo] << "> ";
        else
            cout << "  minigit> ";
        getline(cin, line);

        if (line.empty()) continue;

        string cmd = "", arg1 = "", arg2 = "";
        stringstream ss(line);
        ss >> cmd;

        if (cmd == "exit" || cmd == "quit") {
            cout << "  Goodbye!" << endl;
            break;
        }
        else if (cmd == "repo") {
            ss >> arg1;
            if (arg1 == "create") {
                ss >> arg2;
                if (arg2.empty()) {
                    cout << "  Usage: repo create <name>" << endl;
                } else {
                    bool exists = false;
                    for (int i = 0; i < repoCount; i++) {
                        if (repoNames[i] == arg2) { exists = true; break; }
                    }
                    if (exists) {
                        cout << "  Repository '" << arg2 << "' already exists." << endl;
                    } else if (repoCount >= 20) {
                        cout << "  Maximum repositories reached." << endl;
                    } else {
                        repos[repoCount] = new MiniGit();
                        repoNames[repoCount] = arg2;
                        activeRepo = repoCount;
                        repoCount++;
                        cout << "  Created and switched to repository: " << arg2 << endl;
                    }
                }
            }
            else if (arg1 == "switch") {
                ss >> arg2;
                if (arg2.empty()) {
                    cout << "  Usage: repo switch <name>" << endl;
                } else {
                    bool found = false;
                    for (int i = 0; i < repoCount; i++) {
                        if (repoNames[i] == arg2) {
                            activeRepo = i;
                            found = true;
                            cout << "  Switched to repo: " << arg2 << endl;
                            break;
                        }
                    }
                    if (!found) cout << "  Repository '" << arg2 << "' not found." << endl;
                }
            }
            else if (arg1 == "delete") {
                ss >> arg2;
                if (arg2.empty()) {
                    cout << "  Usage: repo delete <name>" << endl;
                } else {
                    if (activeRepo >= 0 && repoNames[activeRepo] == arg2) {
                        cout << "  Cannot delete the active repo. Switch first." << endl;
                    } else {
                        bool found = false;
                        for (int i = 0; i < repoCount; i++) {
                            if (repoNames[i] == arg2) {
                                delete repos[i];
                                for (int j = i; j < repoCount - 1; j++) {
                                    repos[j] = repos[j + 1];
                                    repoNames[j] = repoNames[j + 1];
                                }
                                repoCount--;
                                if (activeRepo > i) activeRepo--;
                                found = true;
                                cout << "  Deleted repository: " << arg2 << endl;
                                break;
                            }
                        }
                        if (!found) cout << "  Repository '" << arg2 << "' not found." << endl;
                    }
                }
            }
            else {
                cout << "  Usage: repo create|switch|delete <name>" << endl;
            }
        }
        else if (cmd == "repos") {
            cout << "  === Repositories ===" << endl;
            if (repoCount == 0) {
                cout << "  (none — run 'repo create <name>')" << endl;
            } else {
                for (int i = 0; i < repoCount; i++) {
                    if (i == activeRepo)
                        cout << "  * " << repoNames[i] << " (active)" << endl;
                    else
                        cout << "    " << repoNames[i] << endl;
                }
            }
            cout << "  Total: " << repoCount << " repo(s)" << endl;
        }
        else if (cmd == "help") {
            MiniGit temp;
            temp.help();
        }
        else if (activeRepo < 0) {
            cout << "  No repository selected. Run 'repo create <name>' first." << endl;
        }
        else if (cmd == "init") {
            repos[activeRepo]->init();
        }
        else if (cmd == "add") {
            ss >> arg1;
            getline(ss, arg2);
            if (!arg2.empty() && arg2[0] == ' ') arg2 = arg2.substr(1);

            if (arg1.empty()) {
                cout << "  Usage: add <filename> <content>" << endl;
            } else {
                if (arg2.empty()) arg2 = "(empty file)";
                repos[activeRepo]->add(arg1, arg2);
            }
        }
        else if (cmd == "commit") {
            getline(ss, arg1);
            if (!arg1.empty() && arg1[0] == ' ') arg1 = arg1.substr(1);
            if (arg1.empty()) {
                cout << "  Usage: commit <message>" << endl;
            } else {
                repos[activeRepo]->commit(arg1);
            }
        }
        else if (cmd == "log") {
            repos[activeRepo]->log();
        }
        else if (cmd == "status") {
            repos[activeRepo]->status();
        }
        else if (cmd == "diff") {
            ss >> arg1;
            if (arg1.empty()) {
                cout << "  Usage: diff <filename>" << endl;
            } else {
                repos[activeRepo]->diff(arg1);
            }
        }
        else if (cmd == "branch") {
            ss >> arg1;
            if (arg1.empty()) {
                cout << "  Usage: branch <name>" << endl;
            } else {
                repos[activeRepo]->branch(arg1);
            }
        }
        else if (cmd == "checkout") {
            ss >> arg1;
            if (arg1.empty()) {
                cout << "  Usage: checkout <branch-name>" << endl;
            } else {
                repos[activeRepo]->checkout(arg1);
            }
        }
        else if (cmd == "branches") {
            repos[activeRepo]->listBranches();
        }
        else if (cmd == "merge") {
            ss >> arg1;
            if (arg1.empty()) {
                cout << "  Usage: merge <branch-name>" << endl;
            } else {
                repos[activeRepo]->merge(arg1);
            }
        }
        else if (cmd == "undo") {
            repos[activeRepo]->undo();
        }
        else if (cmd == "redo") {
            repos[activeRepo]->redo();
        }
        else if (cmd == "revert") {
            ss >> arg1;
            if (arg1.empty()) {
                cout << "  Usage: revert <commit-id>" << endl;
            } else {
                repos[activeRepo]->revert(arg1);
            }
        }
        else {
            cout << "  Unknown command: " << cmd << ". Type 'help' for options." << endl;
        }
        cout << endl;
    }

    for (int i = 0; i < repoCount; i++) delete repos[i];
    return 0;
}
