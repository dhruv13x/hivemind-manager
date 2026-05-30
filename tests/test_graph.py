import pytest
from unittest.mock import patch
from hm.ui.trees import build_tree_recursive
from rich.tree import Tree

def test_build_tree_recursive():
    deps_map = {
        "infra": [],
        "transfer": ["infra"],
        "worker": ["infra"],
        "subworker": ["worker"]
    }

    tree = Tree("root")
    build_tree_recursive("infra", deps_map, tree)

    # root should have two children: transfer and worker
    assert len(tree.children) == 2

    # one child should have subworker
    child_names = []
    for c in tree.children:
        child_names.append(str(c.label))

    assert any("transfer" in c for c in child_names)
    assert any("worker" in c for c in child_names)
