from typing import Dict, Any, List
from rich.tree import Tree
from .console import console

def build_tree_recursive(node_name: str, deps_map: Dict[str, List[str]], tree: Tree):
    children = [child for child, deps in deps_map.items() if node_name in deps]
    for child in children:
        child_branch = tree.add(f"[cyan]{child}[/cyan]")
        build_tree_recursive(child, deps_map, child_branch)

def print_list_tree(services: Dict[str, Any]) -> None:
    """
    Displays the discovered services.
    """
    if not services:
        console.print("[yellow]No services detected.[/yellow]")
        return

    tree = Tree("[bold]Detected Services[/bold]")
    for svc, meta in sorted(services.items()):
        branch = tree.add(f"[cyan]{svc}[/cyan]")
        deps = meta.get("dependencies", [])
        if deps:
            branch.add(f"Dependencies: {', '.join(deps)}")
        branch.add(f"Path: {meta.get('path', 'N/A')}")

    console.print(tree)

def print_graph_tree(services: Dict[str, Any]) -> None:
    """
    Displays the dependency graph of services.
    """
    if not services:
        console.print("[yellow]No services detected.[/yellow]")
        return

    deps_map = {svc: meta.get("dependencies", []) for svc, meta in services.items()}

    # Find root nodes (nodes with no dependencies)
    roots = [svc for svc, deps in deps_map.items() if not deps]

    # Nodes with dependencies that aren't in the tree (could be missing or external, treat as root for display)
    all_nodes = set(services.keys())
    for svc, deps in deps_map.items():
        if all(dep not in all_nodes for dep in deps) and svc not in roots:
            roots.append(svc)

    tree = Tree("[bold]Service Graph[/bold]")

    for root in sorted(roots):
        branch = tree.add(f"[cyan]{root}[/cyan]")
        build_tree_recursive(root, deps_map, branch)

    console.print(tree)
