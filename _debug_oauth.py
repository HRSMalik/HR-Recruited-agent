"""Debug OAuth: prints the exact authorization URL with scopes Google receives."""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar",
]

flow = InstalledAppFlow.from_client_secrets_file(
    ".credentials/credentials.json", SCOPES
)
auth_url, _ = flow.authorization_url(prompt="consent", include_granted_scopes="false")
print("\n" + "=" * 80)
print("Scopes being requested (raw):")
for s in SCOPES:
    print(f"  - {s}")
print("\nAuthorization URL Google will receive:")
print(auth_url)
print("=" * 80)

# Now open browser and run actual flow
print("\nOpening browser for actual auth (3 scopes should be requested)...")
creds = flow.run_local_server(port=0)
print("\nGranted scopes in token:")
for s in creds.scopes:
    print(f"  - {s}")

# Save token
with open(".credentials/google_token.json", "w") as f:
    f.write(creds.to_json())
print("\nToken saved to .credentials/google_token.json")
