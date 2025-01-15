from collections import OrderedDict
from typing import Union, List, Any, Dict


class Token:
    def __init__(self, type: str, val: Union[str, int, None]):
        self.type = type
        self.val = val

class Lexer:
    def __init__(self, text: str):
        self.pos = 1
        self.text = text
        self.tokens: List[Token] = []

    def get(self) -> Union[str, None]:
        if self.pos <= len(self.text):
            return self.text[self.pos - 1]
        return None

    def tokenize(self):
        brackets_bal = 0
        while self.pos <= len(self.text):
            c = self.get()

            if c.isspace():
                self.pos += 1
            elif c.isalpha():
                self.pos += 1
                self.tokens.append(Token("CHAR", c))
            elif c == '(':
                self.pos += 1
                brackets_bal += 1
                next_char = self.get()
                if next_char == '?':
                    self.pos += 1
                    next2 = self.get()
                    if next2 == ':':
                        self.pos += 1
                        self.tokens.append(Token("NON_GROUP_OPEN", None))
                    elif '1' <= next2 <= '9':
                        self.pos += 1
                        self.tokens.append(Token("REF_GROUP_OPEN", int(next2)))
                    else:
                        raise ValueError(f"Неизвестный символ после ? ожидалось ':' или число, получили {next2}")
                else:
                    self.tokens.append(Token("GROUP_OPEN", None))
            elif c == ')':
                brackets_bal -= 1
                self.pos += 1
                self.tokens.append(Token("CLOSE", None))
            elif c == '*':
                self.pos += 1
                self.tokens.append(Token("STAR", None))
            elif c == '/':
                self.pos += 1
                next_char = self.get()
                if '1' <= next_char <= '9':
                    self.pos += 1
                    self.tokens.append(Token("REF_STR", int(next_char)))
                else:
                    raise ValueError(f"Неизвестный символ после / ожидалось число, получили {next_char}")
            elif c == '|':
                self.pos += 1
                self.tokens.append(Token("ALTER", None))
            else:
                raise ValueError(f"Неизвестный символ {c}")

        if brackets_bal != 0:
            raise ValueError(f"Несбалансированные скобки в регулярном выражении")

class GroupNode:
    def __init__(self, id: int, node):
        self.id = id
        self.node = node

class RefStrNode:
    def __init__(self, id: int):
        self.id = id

class RefGroupNode:
    def __init__(self, id: int, in_groups: List[int]):
        self.id = id
        self.in_groups = in_groups

class NonGroup:
    def __init__(self, node):
        self.node = node

class StarNode:
    def __init__(self, node):
        self.node = node

class CharNode:
    def __init__(self, char: str):
        self.char = char

class ORNode:
    def __init__(self, nodes: List):
        self.nodes = nodes

class ConcatNode:
    def __init__(self, nodes: List):
        self.nodes = nodes

class Parser:
    def __init__(self, tokens: List[Token]):
        self.pos = 1
        self.tokens = tokens
        self.init_group: List[Any] = []
        self.open_bracket: List[int] = []
        self.groups = 0
        self.max_groups = 9
        self.ast = OrderedDict()
        self.ref_str = OrderedDict()

    def get(self) -> Union[Token, None]:
        if self.pos <= len(self.tokens):
            return self.tokens[self.pos - 1]
        return None

    def check(self, token_type: Union[str, None]) -> Token:
        token = self.get()
        if token is None:
            raise ValueError("Неожиданный конец выражения")
        if token_type is not None and token.type != token_type:
            raise ValueError(f"Ожидается {token_type}, найдено {token.type}")
        self.pos += 1
        return token

    def parse(self):
        node = self.alt_parser()
        if self.get() is not None:
            raise ValueError("Лишние символы после корректного выражения")
        self.parse_nodes(node, set(), False)
        return node

    def alt_parser(self):
        nodes = []
        nodes.append(self.union_parse())
        while self.get() is not None and self.get().type == "ALTER":
            self.check("ALTER")
            if self.get() is None or self.get().type in ["ALTER", "CLOSE"]:
                raise ValueError("Неожиданный конец выражения")
            next_node = self.union_parse()
            nodes.append(next_node)
        return nodes[0] if len(nodes) == 1 else ORNode(nodes)

    def union_parse(self):
        nodes = []
        while self.get() is not None and self.get().type not in ["ALTER", "CLOSE"]:
            nodes.append(self.star_parse())
        return nodes[0] if len(nodes) == 1 else ConcatNode(nodes)

    def star_parse(self):
        node = self.bracket_parse()
        while self.get() is not None and self.get().type == "STAR":
            self.check("STAR")
            node = StarNode(node)
        return node

    def bracket_parse(self):
        token = self.get()
        if token is None:
            raise ValueError("Неожиданный конец выражения при ожидании базового выражения")
        if token.type == "GROUP_OPEN":
            self.check("GROUP_OPEN")
            self.groups += 1
            if self.groups > self.max_groups:
                raise ValueError(f"Количество групп {self.groups} превышает {self.max_groups}")
            group_id = self.groups
            self.open_bracket.append(self.groups)
            node = self.alt_parser()
            self.check("CLOSE")
            self.open_bracket.pop()
            self.ast[group_id] = node
            return GroupNode(group_id, node)
        elif token.type == "NON_GROUP_OPEN":
            self.check("NON_GROUP_OPEN")
            node = self.alt_parser()
            self.check("CLOSE")
            return NonGroup(node)
        elif token.type == "REF_GROUP_OPEN":
            self.check("REF_GROUP_OPEN")
            self.check("CLOSE")
            return RefGroupNode(token.val, self.open_bracket.copy())
        elif token.type == "CHAR":
            self.check("CHAR")
            return CharNode(token.val)
        elif token.type == "REF_STR":
            if token.val in self.open_bracket:
                raise ValueError(f"группа {token.val} ещё не дочитана до конца к моменту обращения к ней")
            self.check("REF_STR")
            if token.val not in self.ref_str:
                self.ref_str[token.val] = []
            self.ref_str[token.val].extend(self.open_bracket)
            return RefStrNode(token.val)
        else:
            raise ValueError(f"Некорректный токен: {token}")

    def parse_nodes(self, node, defined_groups, in_alt):
        if isinstance(node, (CharNode, RefStrNode)):
            return defined_groups
        elif isinstance(node, RefGroupNode):
            if self.check_is_init(node):
                raise ValueError(f"Ссылка на группу {node.id} ещё не дочитана до конца к моменту обращения к ней")
            return defined_groups
        elif isinstance(node, GroupNode):
            if in_alt:
                self.init_group.append(node.id)
            new_defined_groups = self.parse_nodes(node.node, defined_groups, in_alt)
            new_defined_groups.add(node.id)
            return new_defined_groups
        elif isinstance(node, (NonGroup, StarNode)):
            return self.parse_nodes(node.node, defined_groups, in_alt)
        elif isinstance(node, ConcatNode):
            current_defined = defined_groups
            for child in node.nodes:
                current_defined = self.parse_nodes(child, current_defined, in_alt)
            return current_defined
        elif isinstance(node, ORNode):
            all_sides = set()
            for child in node.nodes:
                in_alt = True
                child_sides = self.parse_nodes(child, defined_groups, in_alt)
                all_sides.update(child_sides)
            in_alt = False
            return all_sides
        else:
            raise ValueError("Неизвестный тип узла AST при проверке ссылок")

    def check_is_init(self, node):
        if not self.ref_str:
            return False
        for key, value in self.ref_str.items():
            if key in node.in_groups and node.val in value and value:
                return True
        return False

class CFG:
    def __init__(self, ast: OrderedDict, init_group: List[Any]):
        self.ast = ast
        self.init_group = init_group
        self.C = 1
        self.NG = 1
        self.S = 1
        self.rules = OrderedDict()
        self.N = OrderedDict()

    def create_cfg(self, node, Start):
        N = self.cfg(node, None)
        self.rules[Start] = [[N]]

    def cfg(self, node, start):
        if isinstance(node, CharNode):
            N = start if start is not None else f"CH{self.C}"
            self.C += 1
            if N not in self.rules:
                self.rules[N] = []
            self.rules[N].append([node.char])
            return N
        elif isinstance(node, RefStrNode):
            str_id = node.id
            if str_id not in self.ast:
                raise ValueError("Ссылка на несуществующую строку")
            elif str_id in self.init_group:
                raise ValueError("Ссылка на не инициализированную строку")
            if str_id not in self.N:
                self.N[str_id] = f"RF{str_id}"
                sub_N = self.cfg(self.ast[str_id], None)
                N = self.N[str_id]
                if N not in self.rules:
                    self.rules[N] = []
                self.rules[N].append([sub_N])
            return self.N[str_id]
        elif isinstance(node, RefGroupNode):
            str_id = node.id
            if str_id not in self.N:
                self.N[str_id] = f"GR{str_id}"
                if str_id not in self.ast:
                    raise ValueError("Ссылка на несуществующую группу")
                sub_N = self.cfg(self.ast[str_id], None)
                N = self.N[str_id]
                if N not in self.rules:
                    self.rules[N] = []
                self.rules[N].append([sub_N])
            return self.N[str_id]
        elif isinstance(node, GroupNode):
            N = self.N.get(node.id, None)
            if N is None:
                N = f"G{node.id}"
                self.N[node.id] = N
            sub_N = self.cfg(node.node, None)
            if N not in self.rules:
                self.rules[N] = []
            self.rules[N].append([sub_N])
            return N
        elif isinstance(node, NonGroup):
            N = start if start is not None else f"N{self.NG}"
            self.NG += 1
            sub_N = self.cfg(node.node, None)
            if N not in self.rules:
                self.rules[N] = []
            self.rules[N].append([sub_N])
            return N
        elif isinstance(node, StarNode):
            N = start if start is not None else f"ST{self.S}"
            self.S += 1
            sub_N = self.cfg(node.node, None)
            if N not in self.rules:
                self.rules[N] = ['ε']
            self.rules[N].append([sub_N, N])
            return N
        elif isinstance(node, ConcatNode):
            N = start if start is not None else f"C{self.NG + self.C}"
            self.NG += 1
            seq_N = [self.cfg(ch, None) for ch in node.nodes]
            if N not in self.rules:
                self.rules[N] = []
            self.rules[N].append(seq_N)
            return N
        elif isinstance(node, ORNode):
            N = start if start is not None else f"A{self.NG + self.C}"
            self.NG += 1
            for nod in node.nodes:
                br_N = self.cfg(nod, None)
                if N not in self.rules:
                    self.rules[N] = []
                self.rules[N].append([br_N])
            return N
        else:
            raise ValueError("Неизвестный тип узла AST при проверке ссылок")

def print_tree(node, depth=0):
    indent = "  " * depth  # Отступ для визуализации уровня вложенности
    if isinstance(node, CharNode):
        print(f"{indent}CharNode: {node.char}")
    elif isinstance(node, GroupNode):
        print(f"{indent}GroupNode (id={node.id}):")
        print_tree(node.node, depth + 1)
    elif isinstance(node, RefGroupNode):
        print(f"{indent}RefGroupNode (id={node.id}, in_groups={node.in_groups})")
    elif isinstance(node, RefStrNode):
        print(f"{indent}RefStrNode (id={node.id})")
    elif isinstance(node, NonGroup):
        print(f"{indent}NonGroup:")
        print_tree(node.node, depth + 1)
    elif isinstance(node, StarNode):
        print(f"{indent}StarNode:")
        print_tree(node.node, depth + 1)
    elif isinstance(node, ConcatNode):
        print(f"{indent}UnionNode:")
        for child in node.nodes:
            print_tree(child, depth + 1)
    elif isinstance(node, ORNode):
        print(f"{indent}AlterNode:")
        for child in node.nodes:
            print_tree(child, depth + 1)
    else:
        print(f"{indent}UnknownNode: {type(node)}")


def main():
    print("Введите регулярное выражение:")
    text = input()
    lexer = Lexer(text)
    lexer.tokenize()
    print()
    for token in lexer.tokens:
        print(f"{token.type}, {token.val}")
    print()
    parser = Parser(lexer.tokens)
    node = parser.parse()
    print_tree(node, 0)
    cfg = CFG(parser.ast, parser.init_group)
    cfg.create_cfg(node, "S")
    for nt, rhs_list in cfg.rules.items():
        for rhs in rhs_list:
            rhs_str = "ε" if not rhs else " ".join(rhs)
            print(f"{nt} -> {rhs_str}")
    print("=" * 60)

if __name__ == "__main__":
    main()
