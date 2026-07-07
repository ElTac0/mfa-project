import requests

BASE_URL = "https://127.0.0.1:5000"
CA_CERT = "certs/ca.crt"   # trust our local CA

# One session object carries the auth cookie across requests
session = requests.Session()
session.verify = CA_CERT   # validate the server cert against our CA


def register():
    username = input("Choose a username: ")
    password = input("Choose a password: ")
    phone    = input("Phone number (+1XXXXXXXXXX): ")
    r = session.post(f"{BASE_URL}/register", json={
        "username": username, "password": password, "phone": phone
    })
    print(_msg(r))


def login():
    username = input("Username: ")
    password = input("Password: ")
    r = session.post(f"{BASE_URL}/login", json={
        "username": username, "password": password
    })
    print(_msg(r))

    if r.status_code == 200:
        # First factor passed, ask for code
        code = input("Enter the verification code sent to your phone: ")
        r2 = session.post(f"{BASE_URL}/verify", json={
            "username": username, "code": code
        })
        print(_msg(r2))


def dashboard():
    r = session.get(f"{BASE_URL}/dashboard")
    print(_msg(r))


def logout():
    r = session.post(f"{BASE_URL}/logout")
    print(_msg(r))


def _msg(response):
    try:
        data = response.json()
        return data.get("message") or data.get("error") or data
    except Exception:
        return f"[{response.status_code}] {response.text}"


def main():
    actions = {
        "1": ("Register", register),
        "2": ("Login", login),
        "3": ("Access dashboard", dashboard),
        "4": ("Logout", logout),
        "5": ("Quit", None),
    }
    while True:
        print("\n=== MFA Client ===")
        for key, (label, _) in actions.items():
            print(f"  {key}. {label}")
        choice = input("Select: ").strip()

        if choice == "5":
            print("Goodbye.")
            break
        action = actions.get(choice)
        if action:
            action[1]()
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()