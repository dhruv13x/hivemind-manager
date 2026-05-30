from rich.tree import Tree
from rich.text import Text
from typing import Dict, Any

def build_service_tree(services_meta: Dict[str, Any]) -> Tree:
    """
    Builds a basic tree listing all discovered services for 'hm list'.
    """
    tree = Tree("[bold cyan]Detected services[/bold cyan]")

    for svc in sorted(services_meta.keys()):
        meta = services_meta[svc]
        deps = meta.get("dependencies", [])

        svc_text = Text(svc, style="green")
        svc_node = tree.add(svc_text)

        path_str = str(meta.get("path", ""))
        if path_str:
            svc_node.add(f"[dim]Path: {path_str}[/dim]")

        if deps:
            svc_node.add(f"[dim]Depends on: {', '.join(deps)}[/dim]")

    return tree

def build_dependency_graph(services_meta: Dict[str, Any]) -> Tree:
    """
    Builds a tree visualizing dependency relationships for 'hm graph'.
    Roots are services with no incoming dependencies, or we can just show
    services with no dependencies as roots, and recursively attach dependents.
    """
    # 1. Find all dependencies declared
    all_deps = set()
    for meta in services_meta.values():
        all_deps.update(meta.get("dependencies", []))

    # Roots are services that do NOT have any dependencies themselves
    roots = [s for s, m in services_meta.items() if not m.get("dependencies", [])]

    # If there are cycles or everything is a dependency of something else, fallback
    if not roots and services_meta:
        roots = sorted(list(services_meta.keys()))

    tree = Tree("[bold cyan]Dependency Graph[/bold cyan]")

    visited = set()

    def add_node(parent_tree: Tree, service_name: str):
        if service_name in visited:
            parent_tree.add(Text(f"{service_name} (cycle or shared)", style="dim"))
            return

        visited.add(service_name)
        node = parent_tree.add(Text(service_name, style="green"))

        # Find services that depend on this service
        dependents = [s for s, m in services_meta.items() if service_name in m.get("dependencies", [])]
        for dep in sorted(dependents):
            add_node(node, dep)

    for root in sorted(roots):
        add_node(tree, root)

    return tree
