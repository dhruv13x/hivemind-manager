import re
from .config import PROJECT_ROOT

def discover_services():
    """
    Scans the project root for *.hm files and dynamically builds the services registry,
    including dependencies parsed from comments inside each file (e.g., # depends_on: infra).
    """
    services = {}
    for path in sorted(PROJECT_ROOT.glob("*.hm")):
        service_name = path.stem
        dependencies = []

        try:
            with open(path, "r") as f:
                for line in f:
                    # Parse line like "# depends_on: infra, database"
                    match = re.match(r"^\s*#\s*depends_on\s*:\s*(.*)$", line, re.IGNORECASE)
                    if match:
                        deps = match.group(1).split(",")
                        for dep in deps:
                            dep = dep.strip()
                            if dep:
                                dependencies.append(dep)
        except Exception:
            pass

        services[service_name] = {
            "path": path,
            "dependencies": dependencies
        }
    return services
