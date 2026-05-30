from typing import Dict, Any, List
from rich.tree import Tree

def render_services_list(services_meta: Dict[str, Any]) -> Tree:
    """
    Renders a simple rich tree of discovered services for `hm list`.
    """
    tree = Tree("[bold cyan]Detected services[/bold cyan]", guide_style="bold blue")
    for svc, meta in sorted(services_meta.items()):
        node = tree.add(f"[green]✓[/green] [bold]{svc}[/bold]")
        path_str = str(meta.get("path", ""))
        if path_str:
            node.add(f"[dim]path:[/dim] {path_str}")

        deps = meta.get("dependencies", [])
        if deps:
            node.add(f"[dim]depends_on:[/dim] {', '.join(deps)}")

    return tree

def render_dependency_graph(services_meta: Dict[str, Any]) -> Tree:
    """
    Renders a rich tree showing dependency relationships for `hm graph`.
    """
    tree = Tree("[bold magenta]Service Dependency Graph[/bold magenta]", guide_style="bold blue")

    # Simple algorithm: find roots (nodes that no one depends on, or just print all top-levels if complex)
    # Since any service can be started, we can just show each service and what it depends on.

    # Or to make it like the example:
    # infra
    # ├── transfer
    # ├── bypass
    # ├── uab
    # └── sandbox

    # 1. Build an inverted index of "who depends on me"
    dependents = {svc: [] for svc in services_meta}
    for svc, meta in services_meta.items():
        for dep in meta.get("dependencies", []):
            if dep in dependents:
                dependents[dep].append(svc)
            else:
                dependents[dep] = [svc]

    # 2. Find roots (services that have no dependencies)
    roots = [svc for svc, meta in services_meta.items() if not meta.get("dependencies")]

    # If no roots found (cyclic or just all have deps), just use all services
    if not roots:
        roots = list(services_meta.keys())

    def add_children(node: Tree, svc_name: str, visited: set):
        if svc_name in visited:
             # cyclic
             node.add(f"[red](cyclic)[/red] {svc_name}")
             return

        visited.add(svc_name)
        for child in sorted(dependents.get(svc_name, [])):
             child_node = node.add(f"[cyan]{child}[/cyan]")
             add_children(child_node, child, visited.copy())

    for root in sorted(roots):
        root_node = tree.add(f"[bold green]{root}[/bold green]")
        add_children(root_node, root, set())

    return tree
