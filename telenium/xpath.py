# coding=utf-8

import re
import json


class Selector(object):
    def __init__(self, **kwargs):
        super(Selector, self).__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def traverse_tree(self, root):
        if not root:
            return
        yield root
        for child in root.children:
            for result in self.traverse_tree(child):
                yield result

    def match_class(self, widget, classname):
        if not classname.startswith("~"):
            return widget.__class__.__name__ == classname
        bases = [widget.__class__] + list(self.get_bases(widget.__class__))
        bases = [cls.__name__ for cls in bases]
        return classname[1:] in bases

    def get_bases(self, cls):
        for base in cls.__bases__:
            if base.__name__ == 'object':
                break
            yield base
            if base.__name__ == 'Widget':
                break
            for cbase in self.get_bases(base):
                yield cbase

    def execute(self, root):
        return list(self.filter(root, [root]))

    def __add__(self, other):
        return SequenceSelector(first=self, second=other)


class SequenceSelector(Selector):
    first = None
    second = None

    def filter(self, root, items):
        items = self.first.filter(root, items)
        items = self.second.filter(root, items)
        return items

    def __repr__(self):
        return "Sequence({}, {})".format(self.first, self.second)


class AllClassSelector(Selector):
    classname = None

    def filter(self, root, items):
        if not items:
            items = [self.root]
        for item in items:
            for match_item in self.traverse_tree(item):
                if self.match_class(match_item, self.classname):
                    yield match_item

    def __repr__(self):
        return "AllClass(classname={})".format(self.classname)


class ChildrenClassSelector(Selector):
    classname = None

    def filter(self, root, items):
        items = list(items)
        for item in items:
            for child in item.children:
                if self.match_class(child, self.classname):
                    yield child

    def __repr__(self):
        return "ChildrenClass(classname={})".format(self.classname)


class IndexSelector(Selector):
    index = None

    def filter(self, root, items):
        try:
            for index, item in enumerate(reversed(list(items))):
                if index == self.index:
                    yield item
                    return
        except IndexError:
            return

    def __repr__(self):
        return "Index({})".format(self.index)


class AttrExistSelector(Selector):
    attr = None

    def filter(self, root, items):
        for item in items:
            if hasattr(item, self.attr):
                yield item

    def __repr__(self):
        return "AttrExists({})".format(self.attr)


class AttrOpSelector(Selector):
    attr = None
    op = None
    value = None

    def filter(self, root, items):
        op = self.op
        attr = self.attr
        value = json.loads(self.value)
        for item in items:
            if not hasattr(item, attr):
                continue
            value_item = getattr(item, attr)
            if op == "=" and value_item == value:
                yield item
            elif op == "!=" and value_item != value:
                yield item
            elif op == "~=" and value in value_item:
                yield item
            elif op == "!~=" and value not in value_item:
                yield item

    def __repr__(self):
        return "AttrOp(attr={}, op={}, value={})".format(self.attr, self.op,
                                                         self.value)


class XpathParser(object):
    WORD = re.compile("^([~\w]+)")

    def parse(self, expr):
        root = None
        while expr:
            selector = None
            if expr.startswith("//"):
                expr = expr[2:]
                match = re.match(self.WORD, expr)
                if not match:
                    raise Exception("Missing classname for //")
                classname = expr[match.start():match.end()]
                expr = expr[match.end():]
                selector = AllClassSelector(classname=classname)

            elif expr.startswith("/"):
                expr = expr[1:]
                match = re.match(self.WORD, expr)
                if not match:
                    raise Exception("Missing classname for /")
                classname = expr[match.start():match.end()]
                expr = expr[match.end():]
                selector = ChildrenClassSelector(classname=classname)

            elif expr.startswith("["):
                index_nbr = expr.index("]")
                try:
                    # index ?
                    index = int(expr[1:index_nbr])
                    selector = IndexSelector(index=index)
                except:
                    for item in expr[1:index_nbr].split(","):
                        item_selector = self.parse_attr(item)
                        if selector:
                            selector = SequenceSelector(first=selector,
                                                        second=item_selector)
                        else:
                            selector = item_selector
                expr = expr[index_nbr + 1:]

            else:
                raise Exception("Left over during parsing: {}".format(expr))

            if selector:
                if not root:
                    root = selector
                else:
                    root = SequenceSelector(first=root, second=selector)

        return root

    def parse_attr(self, expr):
        if expr.startswith("@"):
            return self.parse_attr_op(expr)
        else:
            #return self.parse_attr_func(expr)
            # why not ?
            raise Exception("Invalid syntax at {}".format(expr))

    def parse_attr_op(self, expr):
        info = re.split(r"(=|!=|~=|!~=)", expr, 1)
        attr = info[0][1:]
        if len(info) == 1:
            return AttrExistSelector(attr=attr)
        elif len(info) == 3:
            return AttrOpSelector(attr=attr, op=info[1], value=info[2])
        else:
            raise Exception("Invalid syntax in {}".format(expr))


if __name__ == "__main__":
    from kivy.lang import Builder
    root = Builder.load_string("""
BoxLayout:
    TextInput
    BoxLayout:
        AnchorLayout:
            TextInput
            TextInput
    Button:
        text: "Hello"
    Button:
        text: "World"
    """)
    parser = XpathParser()
    print parser.parse("//BoxLayout/TextInput").execute(root)
    print parser.parse("//TextInput").execute(root)
    p = parser.parse("//BoxLayout/Button[@text=\"World\"]")
    print p
    print p.execute(root)
