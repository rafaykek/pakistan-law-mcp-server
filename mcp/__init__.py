"""
Pakistan Law MCP Server Package.

This __init__.py extends __path__ to merge with the installed official `mcp` SDK
in site-packages, allowing `import mcp` to access both local modules (like mcp.server)
and the official MCP library modules (like mcp.client, mcp.types, etc.) seamlessly.
"""

import os
import site
import sys

# Extend __path__ to include the site-packages mcp distribution
_site_dirs = []
try:
    _site_dirs.extend(site.getsitepackages())
except Exception:
    pass
if hasattr(site, "getusersitepackages"):
    try:
        _site_dirs.append(site.getusersitepackages())
    except Exception:
        pass
# Also check any sys.path entries with site-packages
for p in sys.path:
    if "site-packages" in p and p not in _site_dirs:
        _site_dirs.append(p)

for base in _site_dirs:
    target = os.path.join(base, "mcp")
    if os.path.isdir(target) and target not in __path__:
        __path__.append(target)
