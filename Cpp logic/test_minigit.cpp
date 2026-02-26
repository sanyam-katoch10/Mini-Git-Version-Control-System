#include <iostream>
#include <cassert>
#include "minigit.h"
using namespace std;

int tests_passed = 0;
int tests_total = 0;

void check(bool condition, string name) {
    tests_total++;
    if (condition) {
        cout << "  PASS: " << name << endl;
        tests_passed++;
    } else {
        cout << "  FAIL: " << name << endl;
    }
}

int main() {
    cout << endl;
    cout << "  ========= MiniGit Test Suite =========" << endl << endl;

    cout << "  --- Hashing ---" << endl;
    string h1 = generateHash("hello world");
    string h2 = generateHash("hello world");
    string h3 = generateHash("different text");
    check(h1 == h2, "Same input -> same hash");
    check(h1 != h3, "Different input -> different hash");
    check(h1.length() > 0, "Hash is non-empty");
    cout << endl;

    cout << "  --- File Storage (Array) ---" << endl;
    FileState fs;
    fs.addFile("main.cpp", "#include <iostream>");
    fs.addFile("readme.txt", "Hello");
    check(fs.fileCount == 2, "Added 2 files");
    check(fs.getFile("main.cpp") != NULL, "Find existing file");
    check(fs.getFile("missing.txt") == NULL, "Missing file returns NULL");

    fs.addFile("main.cpp", "int main() {}");
    check(fs.fileCount == 2, "Update doesn't duplicate");
    check(fs.getFile("main.cpp")->content == "int main() {}", "Content updated");

    FileState snapshot = fs.copy();
    check(snapshot.fileCount == 2, "Snapshot deep copy works");

    fs.removeFile("readme.txt");
    check(fs.fileCount == 1, "Remove shrinks array");
    check(snapshot.fileCount == 2, "Snapshot unaffected by remove");
    cout << endl;

    cout << "  --- Commit Tree (Binary Tree) ---" << endl;
    Commit* c1 = new Commit("abc123", "Initial commit");
    c1->snapshot = snapshot.copy();
    check(c1->parent == NULL, "Root has no parent");
    check(c1->childCount == 0, "Root has no children");

    Commit* c2 = new Commit("def456", "Second commit");
    c2->parent = c1;
    c1->children[c1->childCount++] = c2;
    check(c2->parent == c1, "Child linked to parent");
    check(c1->childCount == 1, "Parent has 1 child");

    Commit* c3 = new Commit("ghi789", "Branch commit");
    c3->parent = c1;
    c1->children[c1->childCount++] = c3;
    check(c1->childCount == 2, "Parent has 2 children (branching)");
    cout << endl;

    cout << "  --- Custom Stack (Undo/Redo) ---" << endl;
    CommitStack undoStack;
    CommitStack redoStack;
    check(undoStack.isEmpty(), "Stack starts empty");

    undoStack.push(c1);
    undoStack.push(c2);
    check(undoStack.size() == 2, "Push increases size");
    check(undoStack.peek() == c2, "Peek returns top");

    Commit* popped = undoStack.pop();
    redoStack.push(popped);
    check(popped == c2, "Pop returns correct item");
    check(undoStack.size() == 1, "Pop decreases size");
    check(redoStack.size() == 1, "Redo stack has item");

    Commit* redone = redoStack.pop();
    undoStack.push(redone);
    check(redone == c2, "Redo pops correct item");
    check(undoStack.size() == 2, "Undo stack restored");
    cout << endl;

    cout << "  --- Branch List (Linked List) ---" << endl;
    BranchList bl;
    bl.addBranch("main", c2);
    bl.addBranch("feature", c3);
    check(bl.count() == 2, "2 branches in list");
    check(bl.findBranch("main") != NULL, "Find main branch");
    check(bl.findBranch("feature") != NULL, "Find feature branch");
    check(bl.findBranch("missing") == NULL, "Missing branch returns NULL");
    check(bl.active->name == "main", "First branch is active");

    bl.switchBranch("feature");
    check(bl.active->name == "feature", "Switched to feature");

    bl.switchBranch("main");
    bl.deleteBranch("feature");
    check(bl.count() == 1, "Delete removes branch");
    check(bl.findBranch("feature") == NULL, "Deleted branch gone");
    cout << endl;

    cout << "  --- Recursion (History Traversal) ---" << endl;
    int depth = countCommits(c2);
    check(depth == 2, "countCommits returns 2 for c2->c1");

    int depth1 = countCommits(c1);
    check(depth1 == 1, "countCommits returns 1 for root");

    int depth0 = countCommits(NULL);
    check(depth0 == 0, "countCommits returns 0 for NULL");
    cout << endl;

    cout << "  --- Backtracking (DFS Find) ---" << endl;
    Commit* found = findCommit(c1, "ghi789");
    check(found == c3, "DFS finds c3 by ID");

    Commit* found2 = findCommit(c1, "abc123");
    check(found2 == c1, "DFS finds root by ID");

    Commit* notFound = findCommit(c1, "zzz000");
    check(notFound == NULL, "DFS returns NULL for missing");

    Commit* hist = findInHistory(c2, "abc123");
    check(hist == c1, "findInHistory walks parent chain");
    cout << endl;

    cout << "  =======================================" << endl;
    cout << "  Results: " << tests_passed << " / " << tests_total << " passed" << endl;
    if (tests_passed == tests_total)
        cout << "  ALL TESTS PASSED!" << endl;
    else
        cout << "  SOME TESTS FAILED!" << endl;
    cout << "  =======================================" << endl << endl;

    delete c1;
    delete c2;
    delete c3;

    return (tests_passed == tests_total) ? 0 : 1;
}
