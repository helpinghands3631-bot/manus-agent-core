"""
verify_opik.py
--------------
Quick verification that Opik is connected to your Comet workspace.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import opik

print("=" * 60)
print("  Opik Connection Verification")
print("=" * 60)

api_key = os.getenv("OPIK_API_KEY", "NOT SET")
workspace = os.getenv("OPIK_WORKSPACE", "NOT SET")
project = os.getenv("OPIK_PROJECT_NAME", "NOT SET")

print(f"\n  OPIK_API_KEY:        {'***' + api_key[-6:] if len(api_key) > 6 else api_key}")
print(f"  OPIK_WORKSPACE:      {workspace}")
print(f"  OPIK_PROJECT_NAME:   {project}")

print("\n  Attempting to connect to Comet/Opik...")

try:
    # Configure Opik to use cloud
    opik.configure(
        api_key=api_key,
        workspace=workspace,
        use_local=False,
    )
    
    # Create a test client to verify the connection
    client = opik.Opik(
        project_name=project,
        workspace=workspace,
    )
    
    print(f"  Connection successful!")
    print(f"  Dashboard: https://www.comet.com/opik/{workspace}/home")
    
    # Log a test trace to confirm write access
    trace = client.trace(
        name="connection-verification",
        input={"test": "Verifying Opik connection from manus-agent-core"},
        output={"status": "connected", "workspace": workspace},
        tags=["verification", "setup"],
        metadata={"source": "verify_opik.py"},
    )
    trace.end()
    
    print(f"  Test trace logged successfully!")
    print(f"  Check it at: https://www.comet.com/opik/{workspace}/projects")
    
except Exception as exc:
    print(f"\n  Connection FAILED: {type(exc).__name__}: {exc}")
    print(f"\n  Troubleshooting:")
    print(f"  1. Verify your OPIK_API_KEY is correct")
    print(f"  2. Verify workspace '{workspace}' exists at comet.com")
    print(f"  3. Try running: opik configure")

print(f"\n{'=' * 60}")
