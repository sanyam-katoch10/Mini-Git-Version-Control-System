#ifndef MINIGIT_H
#define MINIGIT_H

#include <iostream>
#include <string>
#include <ctime>
using namespace std;

class File {
public:
    string name;
    string content;
};

class FileState {
public:
    File files[100];
    int fileCount;

    FileState() : fileCount(0) {}

    void addFile(string name, string content) {
        for (int i = 0; i < fileCount; i++) {
            if (files[i].name == name) {
                files[i].content = content;
                return;
            }
        }
        files[fileCount].name = name;
        files[fileCount].content = content;
        fileCount++;
    }

    void removeFile(string name) {
        for (int i = 0; i < fileCount; i++) {
            if (files[i].name == name) {
                for (int j = i; j < fileCount - 1; j++) {
                    files[j] = files[j + 1];
                }
                fileCount--;
                return;
            }
        }
    }

    File* getFile(string name) {
        for (int i = 0; i < fileCount; i++) {
            if (files[i].name == name)
                return &files[i];
        }
        return NULL;
    }

    FileState copy() {
        FileState fs;
        fs.fileCount = fileCount;
        for (int i = 0; i < fileCount; i++) {
            fs.files[i].name = files[i].name;
            fs.files[i].content = files[i].content;
        }
        return fs;
    }

    void printFiles() {
        if (fileCount == 0) {
            cout << "  (no files)" << endl;
            return;
        }
        for (int i = 0; i < fileCount; i++) {
            cout << "  [" << i << "] " << files[i].name << endl;
        }
    }
};

string generateHash(string data) {
    long long hash = 0;
    for (int i = 0; i < (int)data.length(); i++) {
        hash = hash * 31 + data[i];
    }
    if (hash < 0) hash = -hash;

    string result = "";
    long long temp = hash;
    char hexChars[] = "0123456789abcdef";
    for (int i = 0; i < 8; i++) {
        result = hexChars[temp % 16] + result;
        temp /= 16;
    }
    return result;
}

string getTimestamp() {
    time_t now = time(0);
    string ts = ctime(&now);
    if (!ts.empty() && ts[ts.length() - 1] == '\n')
        ts = ts.substr(0, ts.length() - 1);
    return ts;
}

class Commit {
public:
    string commitId;
    string message;
    string timestamp;
    Commit* parent;
    Commit* children[10];
    int childCount;
    FileState snapshot;

    Commit(string id, string msg) {
        commitId = id;
        message = msg;
        timestamp = getTimestamp();
        parent = NULL;
        childCount = 0;
    }
};

class CommitStack {
private:
    Commit* data[100];
    int top;

public:
    CommitStack() : top(-1) {}

    void push(Commit* c) {
        if (top < 99) {
            data[++top] = c;
        }
    }

    Commit* pop() {
        if (top >= 0) {
            return data[top--];
        }
        return NULL;
    }

    Commit* peek() {
        if (top >= 0) return data[top];
        return NULL;
    }

    bool isEmpty() { return top == -1; }

    int size() { return top + 1; }

    void clear() { top = -1; }
};

class Branch {
public:
    string name;
    Commit* head;
    Branch* next;

    Branch(string n, Commit* h) {
        name = n;
        head = h;
        next = NULL;
    }
};

class BranchList {
public:
    Branch* first;
    Branch* active;

    BranchList() : first(NULL), active(NULL) {}

    ~BranchList() {
        Branch* curr = first;
        while (curr) {
            Branch* temp = curr;
            curr = curr->next;
            delete temp;
        }
    }

    void addBranch(string name, Commit* head) {
        Branch* newBranch = new Branch(name, head);
        if (first == NULL) {
            first = newBranch;
        } else {
            Branch* curr = first;
            while (curr->next != NULL) {
                curr = curr->next;
            }
            curr->next = newBranch;
        }
        if (active == NULL) active = newBranch;
    }

    Branch* findBranch(string name) {
        Branch* curr = first;
        while (curr != NULL) {
            if (curr->name == name) return curr;
            curr = curr->next;
        }
        return NULL;
    }

    bool switchBranch(string name) {
        Branch* b = findBranch(name);
        if (b != NULL) {
            active = b;
            return true;
        }
        return false;
    }

    bool deleteBranch(string name) {
        if (active != NULL && active->name == name) {
            return false;
        }
        if (first == NULL) return false;

        if (first->name == name) {
            Branch* temp = first;
            first = first->next;
            delete temp;
            return true;
        }

        Branch* curr = first;
        while (curr->next != NULL) {
            if (curr->next->name == name) {
                Branch* temp = curr->next;
                curr->next = curr->next->next;
                delete temp;
                return true;
            }
            curr = curr->next;
        }
        return false;
    }

    void printBranches() {
        Branch* curr = first;
        while (curr != NULL) {
            if (curr == active)
                cout << "  * " << curr->name << " (active)" << endl;
            else
                cout << "    " << curr->name << endl;
            curr = curr->next;
        }
    }

    int count() {
        int c = 0;
        Branch* curr = first;
        while (curr != NULL) {
            c++;
            curr = curr->next;
        }
        return c;
    }
};

void printHistory(Commit* node) {
    if (node == NULL) return;
    cout << "  commit " << node->commitId << endl;
    cout << "  Date:   " << node->timestamp << endl;
    cout << "  Msg:    " << node->message << endl;
    cout << "  Files:  " << node->snapshot.fileCount << endl;
    cout << endl;
    printHistory(node->parent);
}

int countCommits(Commit* node) {
    if (node == NULL) return 0;
    return 1 + countCommits(node->parent);
}

Commit* findCommit(Commit* root, string id) {
    if (root == NULL) return NULL;
    if (root->commitId == id) return root;

    for (int i = 0; i < root->childCount; i++) {
        Commit* result = findCommit(root->children[i], id);
        if (result != NULL) return result;
    }
    return NULL;
}

Commit* findInHistory(Commit* node, string id) {
    if (node == NULL) return NULL;
    if (node->commitId == id) return node;
    return findInHistory(node->parent, id);
}

#endif
