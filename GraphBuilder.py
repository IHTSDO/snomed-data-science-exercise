from Node import *


class GraphBuilder:
    def __init__(self):
        self.allNodes = {}
        self.rootNode = None

    def add_child_parent_link(self, child_code, parent):
        parent_code = parent['code']
        parent_node = self.allNodes.setdefault(parent_code, Node(parent_code))
        parent_node.set_label(parent['label'])
        child_node = self.allNodes.setdefault(child_code, Node(child_code))
        parent_node.add_child(child_node)

        if parent_code == 138875005:  # Keep root for debug browsing
            self.rootNode = parent_node

    def get_node(self, code):
        return self.allNodes.get(code)

    def get_ancestors(self, code, upward_level_limit):
        ancestors = set()
        node = self.get_node(code)
        if node:
            self._collect_ancestors(node, ancestors, upward_level_limit)
        return ancestors

    def get_root_node(self):
        return self.rootNode

    def _collect_ancestors(self, node, ancestors, upwardLevelLimit):
        if upwardLevelLimit > 0:
            for parent in node.get_parents():
                ancestors.add(parent.get_code())
                self._collect_ancestors(parent, ancestors, upwardLevelLimit - 1)
