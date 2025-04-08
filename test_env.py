import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Required environment variables
required_vars = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION"
]

# Check each variable
missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if not value:
        missing_vars.append(var)
    else:
        print(f"✓ {var} is set")

if missing_vars:
    print("\nMissing environment variables:")
    for var in missing_vars:
        print(f"✗ {var} is not set")
else:
    print("\nAll required environment variables are set!") 