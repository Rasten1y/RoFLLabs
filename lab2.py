import json
import requests

ip = "http://localhost:8080"

session = requests.Session()


class Table:
    def __init__(self):
        self.pref = ["ε"]
        self.is_main = [True]
        self.suff = ["ε"]
        self.data = [[0]]
        self.alphabet = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        

def full(t):
    n = len(t.pref)
    for i in range(n):
        if not t.is_main[i]:
            unique = True
            for j in range(n):
                if t.data[i] == t.data[j] and t.is_main[j]:
                    unique = False
                    break
            if unique:
                t.is_main[i] = True

def add_pref(t):
    n = len(t.pref)
    for i in range(n):
        for j in range(len(t.alphabet)):
            new_pref = t.pref[i] + t.alphabet[j] if t.pref[i] != "ε" else t.alphabet[j]
            if new_pref not in t.pref:
                t.pref.append(new_pref)
                t.is_main.append(False)
                wordlist = []
                for k in range(len(t.suff)):
                    suff = t.suff[k]
                    word = "ε" if new_pref == "ε" and suff == "ε" else (
                        suff if new_pref == "ε" else (new_pref if suff == "ε" else new_pref + suff))
                    wordlist.append(word)
                data = {"wordList": wordlist}
                response = session.post(f"{ip}/check-word-batch", json=data)
                temp = []
                if response.status_code == 200:
                    parsed_response = response.json()
                    for k in range(len(t.suff)):
                        if parsed_response["responseList"][k] == True:
                            temp.append(1)
                        else:
                            temp.append(0)
                t.data.append(temp)

def fill_elem(pref, suff):
    word = "ε" if pref == "ε" and suff == "ε" else (suff if pref == "ε" else (pref if suff == "ε" else pref + suff))
    data = {"word": word}
    response = session.post(f"{ip}/checkWord", json=data)
    if response.status_code == 200:
        parsed_response = response.json()
        if parsed_response["response"] == "1":
            return 1
        return 0
    return 0

def fill(t):
    for i in range(len(t.pref)):
        for j in range(len(t.suff)):
            t.data[i][j] = fill_elem(t.pref[i], t.suff[j])

def counter(t, contr):
    word = contr[-1]
    for k in range(len(contr)):
        if word not in t.suff:
           t.suff.append(word)
           for i in range(len(t.pref)):
              t.data[i].append(fill_elem(t.pref[i], word))
        if len(word) < len(contr):
            word = contr[-k-2] + word

def is_equiv(t):
    main_pref = ""
    n_main_pref = ""
    data_main = ""
    data_n_main = ""

    for i in range(len(t.pref)):
        if t.is_main[i]:
            main_pref += " " + t.pref[i]
            data_main += " " + " ".join(map(str, t.data[i]))
        else:
            n_main_pref += " " + t.pref[i]
            data_n_main += " " + " ".join(map(str, t.data[i]))

    suffixes = " ".join(t.suff)
    data_main += data_n_main
    main_pref = main_pref.strip()
    n_main_pref = n_main_pref.strip()
    data_main = data_main.strip()
    suffixes = suffixes.strip()

    data = {
        "main_prefixes": main_pref,
        "non_main_prefixes": n_main_pref,
        "suffixes": suffixes,
        "table": data_main
    }

    response = session.post(f"{ip}/checkTable", json=data)
    if response.status_code == 200:
        parsed_response = response.json()
        if parsed_response["response"] == "true":
            print("Finish!!!")
            return True
        elif parsed_response["type"] == "false":
            print("Нашли слово вне языка: ", parsed_response["response"])
            counter(t, parsed_response["response"])
            return False
        else:
            print(parsed_response["type"],parsed_response["response"], t.data[i][0])
            print(suffixes)
            print(main_pref)
            print(n_main_pref)
            counter(t, parsed_response["response"])
            return False
    return False

def main():
    t = Table()
    session.post(f"{ip}/generate", json={
            "mode": "fixed",
            "size":5
        }
    )

    while True:
        add_pref(t)
        #fill(t)
        full(t)
        if is_equiv(t):
            print("  ", end="")
            for j in range(len(t.suff)):
                if t.is_main[j]:
                    print(t.suff[j], end=" ")
            print()
            for i in range(len(t.pref)):
                print(t.pref[i], end=" ")
                for j in range(len(t.suff)):
                    print(t.data[i][j], end=" ")
                print()
            break

if __name__ == "__main__":
    main()