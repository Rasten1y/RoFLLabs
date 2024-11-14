#include <iostream>
#include <vector>
#include <string>
#include <nlohmann/json.hpp>
#include "httplib.h"
using namespace std;

struct Table {
    vector<string> pref;
    vector<bool> is_main;
    vector<string> suff;
    vector<vector<int>> data;
};

void full(Table& t) {
    vector<int> toDelete;
    int n = t.pref.size();
    for (int i = 0; i < n; ++i) {
        if (!t.is_main[i]) {
            bool unique = true;
            for (int j = 0; j < n; ++j) {
                if (t.data[i] == t.data[j] && t.is_main[j]) {
                    unique = false;
                    break;
                }
            }
            if (unique) {
                t.is_main[i] = true;
            }
        }
    }
};

void add_pref(Table& t) {
    int n = t.pref.size();
    for (int i = 0; i < n; ++i) {
        if (t.is_main[i] && find(t.pref.begin(), t.pref.end(), t.pref[i]+"L") == t.pref.end()) {
            t.pref.push_back(t.pref[i]+"L");
            t.is_main.push_back(false);
            t.data.push_back({0});
        }
        if (find(t.pref, t.pref+n, t.pref[i]+"R") == end(t.pref)) {
            t.pref.push_back(t.pref[i]+"R")
            t.is_main.push_back(false);
            vector <int> a;
            for (int j = 0; j < t.suff.size(); ++j){
                a.push_back(0);
            }
            t.data.push_back(a);
        }
    }
};

int fill_elem(const string& pref, const string& suff) {
    string word;
    if (pref == "ε" && suff == "ε") word = "ε";
    else if (pref == "ε") word = suff;
    else if (suff == "ε") word = pref;
    else word = pref + suff;

    json data = {{"word", word}};
    httplib::Client cli("http://localhost:8095");
    auto res = cli.Post("/checkWord", data.dump(), "application/json");

    if (res && res->status == 200) {
        auto parsed_response = json::parse(res->body);
        return parsed_response["response"] ? 1 : 0;
    }
    return 0;
};

void fill(Table& t) {
    for (int i  = 0; i < t.pref.size(); ++i) {
        for (int j = 0; j < t.suff.size(); ++j) {
            t.data[i][j] = fill_elem(t.pref[i], t.suff[j]);
        }
    }
};

void counter(Table& t, int start_suffix, const string& contr) {
    cout << contr << endl;
    for (int l = 1; l <= contr.size(); ++l) {
        string a = contr.substr(contr.size() - l);
        if (find(t.suff.begin(), t.suff.end(), a) == t.suff.end()) {
            t.suff.push_back(a);
        }
    }
    fill(t);
};

bool is_equiv(Table& t) {
    vector<string> main_pref;
    vector<string> n_main_pref;
    vector<vector<int>> data_main;
    vector<vector<int>> data_n_main;
    for (int i = 0; i < t.pref.size(); ++i) {
        if (t.is_main[i]) {
            main_pref.push_back(t.pref[i]);
            data_main.push_back(t.data[i]);
        }
        else {
            n_main_pref.push_back(t.pref[i]);
            data_n_main.push_back(t.data[i]);
        }
    }
    for (int i = 0; i < data_n_main.size(); ++i) {
        data_main.push_back(data_n_main[i]);
    }
        json data = {
        {"main_prefixes", main_pref},
        {"non_main_prefixes", n_main_pref},
        {"suffixes", t.suffix},
        {"table", data_main}
    };

    httplib::Client cli("http://localhost:8095");
    auto res = cli.Post("/checkTable", data.dump(), "application/json");

    if (res && res->status == 200) {
        auto parsed_response = json::parse(res->body);
        if (parsed_response["response"].is_null()) {
            cout << "Finish!!!" << endl;
            return true;
        } else {
            counter(t, t.suffix.size() + 1, parsed_response["response"]);
            return false;
        }
    }
    cout << "Error: " << res->status << endl;
    return true;
};

int main() {
    Table t;
    t.pref = {"ε"};
    t.is_main = {true};
    t.suff = {"ε"};
    t.data = {{0}};
    while (true) {
        add_pref(t);
        fill(t);
        full(t);
        if (is_equiv(t)){
            cout << "  ";
            for (int j = 0; j < t.suff.size(); ++j) {
                cout << t.suff[j] << " ";
            }
            cout << endl;
            for (int i = 0; i < t.pref.size(); ++i) {
                cout << t.pref[i] << " ";
                for (int j = 0; j < t.suff.size(); ++j) {
                    cout << t.data[i][j] << " ";
                }
                cout << endl;
            }
            break;
        }
    }
    return 0;
};