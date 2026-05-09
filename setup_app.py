import base64
import hashlib
import json
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from google_auth_oauthlib.flow import Flow

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = "credentials.json"
MEMBERS_FILE = "members.json"
TOKENS_DIR = Path("tokens")
TOKENS_DIR.mkdir(exist_ok=True)

# Allow HTTP for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def _pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _build_flow(state=None):
    return Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for("oauth_callback", _external=True),
    )


@app.route("/")
def index():
    return render_template("setup.html")


@app.route("/oauth/start", methods=["POST"])
def oauth_start():
    session["form_data"] = {
        "name": request.form["name"].strip(),
        "slack_id": request.form["slack_id"].strip(),
        "linear_key": request.form["linear_key"].strip(),
        "github_username": request.form["github_username"].strip(),
        "role": request.form["role"],
    }

    code_verifier, code_challenge = _pkce_pair()
    session["code_verifier"] = code_verifier

    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    flow = _build_flow(state=session["oauth_state"])
    flow.fetch_token(
        authorization_response=request.url,
        code_verifier=session["code_verifier"],
    )

    creds = flow.credentials
    name = session["form_data"]["name"]
    safe_name = name.replace(" ", "_")
    token_path = TOKENS_DIR / f"{safe_name}.json"

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    token_path.write_text(json.dumps(token_data, indent=2))

    session["google_token_path"] = str(token_path)
    return redirect(url_for("submit"))


@app.route("/submit")
def submit():
    form_data = session.get("form_data")
    token_path = session.get("google_token_path")

    if not form_data or not token_path:
        return redirect(url_for("index"))

    member = {
        "name": form_data["name"],
        "slack_id": form_data["slack_id"],
        "linear_key": form_data["linear_key"],
        "github_username": form_data["github_username"],
        "google_token_path": token_path,
        "role": form_data["role"],
    }

    members = []
    if Path(MEMBERS_FILE).exists():
        with open(MEMBERS_FILE) as f:
            members = json.load(f)

    members = [m for m in members if m["name"] != member["name"]]
    members.append(member)

    with open(MEMBERS_FILE, "w") as f:
        json.dump(members, f, indent=2)

    session.clear()
    return redirect(url_for("success"))


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
