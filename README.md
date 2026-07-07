
## This was tested on VSCode powershell and MacBook Termianl
## If you use regular Windows powershell you can run into permission road blocks
## Try "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass" if having permission problems 
## Make sure to have git installed as an extention or on your device


## Setup
### 1. Clone the repository and open VSCODE

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd mfa-project
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a file named `.env` in the project root:

```
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_APP_PASSWORD=your_16_char_app_password
SMS_GATEWAY=@vtext.com
FLASK_SECRET_KEY=your_long_random_secret
```

- **EMAIL_ADDRESS** — the Gmail account that sends verification codes
- **EMAIL_APP_PASSWORD** — a Google App Password (Google Account → Security → App Passwords;
  requires 2-Step Verification). Not your normal Gmail password.
- **SMS_GATEWAY** — your mobile carrier's email-to-SMS domain. Common values:
  | Carrier    | Gateway                    |
  |------------|----------------------------|
  | Verizon    | `@vtext.com`               |
  | AT&T       | `@txt.att.net`             |
  | T-Mobile   | `@tmomail.net`             |
  | Google Fi  | `@msg.fi.google.com`       |
- **FLASK_SECRET_KEY** — a long random string used to sign session cookies. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### 5. Initialize the database

```powershell
python init_db.py
```

This creates `mfa.db` with the `users` table.

### 6. Generate TLS certificates

From the project root, using Git Bash (Windows) or a terminal (macOS/Linux):
## BASH is manditory for windows
## ----------------------------------------------------------------------------------

```bash 
cd certs

# Create the local Certificate Authority
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt -subj "//CN=MFA-Local-CA"

# Create the server key
openssl genrsa -out server.key 2048
```

Then generate and sign the server certificate:

```bash
# Certificate signing request (with Subject Alternative Name)
openssl req -new -key server.key -out server.csr -config server.cnf

# Sign it with the local CA, carrying the SAN through
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 -extfile server.cnf -extensions v3_req

cd ..
```
## ----------------------------------------------------------------------------------
## Running the Application
### Start the server

In one terminal (with the virtual environment active):

```bash
python app.py
```

The server runs on `https://127.0.0.1:5000`.

### Run the client

In a second terminal (with the virtual environment active):

```bash
python client.py
```

You will see a menu:

```
=== MFA Client ===
  1. Register
  2. Login
  3. Access dashboard
  4. Logout
  5. Quit
```
**Typical flow:**
1. Choose **Register** and provide a username, password, and phone number (format `+1XXXXXXXXXX`).
2. Choose **Login** and enter your credentials. On success, a code is texted to your phone.
3. Enter the verification code when prompted.
4. Choose **Access dashboard** to view the protected resource.
