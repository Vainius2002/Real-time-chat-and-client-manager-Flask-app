# Flask Project Showcase

This repository contains two Flask-based web applications built to demonstrate backend development with Python, including real-time communication, database management, and file uploads.

---

## 💬 1. Chat App

**Features:**
- User registration & login
- Add friends
# Flask Project Showcase

This repository contains two Flask-based web applications that demonstrate backend development using Python. They include user authentication, real-time chat, file uploads, and database operations using SQLite.

---

## 💬 1. Chat App

**Features:**
- User registration & login
- Add/remove friends
- Real-time chat using Flask-SocketIO
- Notifications and messaging system
- SQLite database for user data

---

## 🗂️ 2. Client Manager App

**Features:**
- Login system (`admin` / `123`)
- Create, search, and edit client profiles
- Upload and delete images for each client
- SQLite database stores client info
- Uploaded images are saved locally in a folder

---

## 🚀 How to Run

### 🔹 1. Chat App (test.py)

1. **Double-click `test.py`** to start the Flask server.
2. Open `templates/convo.html` in your browser.
3. **Register** a new user with a name and password.
4. Press **“Search Friends”** to find other users (you can create more accounts if needed).
5. Press **“Add”** to add a friend.
6. Open **“Friend List”**, choose a friend, then **press “Chat.”**
7. Messages will be delivered if both users added each other.
8. You’ll get notified when friends message you — if you haven't opened the chat yet.

---

### 🔹 2. Client Manager (info.py)

1. Create a folder named `uploads` inside your main `flasks app` directory.
2. Open `info.py` in VS Code or any editor.
3. In the `UPLOAD_FOLDER` variable, set the full path to the `uploads` folder on your PC.
4. Save the file.
5. **Double-click `info.py`** to start the Flask server.
6. Open `templates/info.html` in your browser.

**Usage:**
- Login with:  
  `username: admin`  
  `password: 123`
- Press **“Ieskoti”** to search for clients.
- Press **“Sukurti”** to create a new client.
- Press **“Koreguoti”** to edit client details, delete images, or upload new ones.

---

## 💡 Notes

- Make sure `uploads/` exists before starting `info.py`.
- These apps are not hosted — they're meant to run locally for demonstration.
- SocketIO may require `eventlet` or `gevent` installed — included in `requirements.txt`.

---

## 🧪 Requirements

Install all dependencies in one step:

```bash
pip install -r requirements.txt

  