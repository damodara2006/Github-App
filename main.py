import os
import time
import json
import jwt
import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
load_dotenv()

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY = Path("github_app333.pem").read_text()
GITHUB_API = "https://api.github.com"

app = FastAPI()

# --------------------------------------------------
# JWT GENERATION (GitHub App Authentication)
# --------------------------------------------------
def generate_github_jwt() -> str:
    now = int(time.time())
    print(time.time(), "time", int(time.time()))
    payload = {
        "iat": now - 60,
        "exp": now + 600,   # max 10 minutes
        "iss": APP_ID
    }
    print("payload ", payload)

    token = jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm="RS256"
    )

    return token

# --------------------------------------------------
# INSTALLATION TOKEN (REAL BEARER TOKEN)
# --------------------------------------------------
async def get_installation_token(installation_id: int) -> str:
    jwt_token = generate_github_jwt()
    # print(jwt_token)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json"
            }
        )
    # print(json.dumps(response.json(), indent=2))
    response.raise_for_status()
    return response.json()["token"]

# --------------------------------------------------
# GITHUB API CALLS
# --------------------------------------------------
async def get_org_members(org: str, token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{GITHUB_API}/orgs/{org}/members",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
    res.raise_for_status()
    return res.json()

async def get_repositories(token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{GITHUB_API}/installation/repositories",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
    res.raise_for_status()
    return res.json()

async def get_access(token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{GITHUB_API}/user/installations",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
    # res.raise_for_status()
    return res.json()
# --------------------------------------------------
# WEBHOOK (INSTALLATION EVENT)
# --------------------------------------------------
@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.json()
    print("🔔 Webhook received:")
    print(json.dumps(payload, indent=2))

    if payload.get("action") == "created":
        installation_id = payload["installation"]["id"]
        org = payload["installation"]["account"]["login"]

        print("✅ App Installed")
        print("Org:", org)
        print("Installation ID:", installation_id)

        # TODO: Save org + installation_id in DB

    return {"status": "ok"}

async def mfa_org(token : str, org : str):
    print(org, token)
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{GITHUB_API}/orgs/{org}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
        print(res)
    # res.raise_for_status()
    return res.json()
# --------------------------------------------------
# TEST ENDPOINTS
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "GitHub App Backend Running ✅"}

@app.get("/org/{org}/members")
async def fetch_members(org: str, installation_id: int):
    token = await get_installation_token(installation_id)
    return await get_org_members(org, token)

@app.get("/repos")
async def fetch_repos(installation_id: int):
    token = await get_installation_token(installation_id)
    return await get_repositories(token)

@app.get("/access")
async def fetch_access(installation_id: int):
    token = await get_installation_token(installation_id)
    return await get_access(token)

@app.get("/mfa")
async def fetch_mfa(installation_id: int, org:str):
    token = await get_installation_token(installation_id)
    return await mfa_org(token, org)