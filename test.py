from flask import Flask,  request, render_template
from flask_socketio import emit, SocketIO
import sqlite3



web = Flask(__name__)
# integravau ssocketio i flask appa
socketio = SocketIO(web)

@web.route("/")
def hello():
    return render_template("convo.html")

# conn = sqlite3.connect("users.db")
# cursor = conn.cursor()


# cursor.execute("DELETE FROM users")
# conn.commit()
# cursor.execute("DELETE FROM friends")
# conn.commit()
# cursor.execute("DELETE FROM chats")
# conn.commit()
# conn.close()





# I get clients sids whhen they first connect, and store them globally
username_dict = {}
@socketio.on('connect')
def get_info():
    # getting clients sid, to send messages to
    SID = request.sid 
    print(f'Clients sid: {SID}')

    # Applying sid if it has not been in username_dict, into the username_dict
    global username_dict
    if "sid" not in username_dict:
        username_dict["sid"] = {}

    username_dict["sid"][SID] = {}
        


# we get from client (js) register inputs (username, password)
@socketio.on('register')
def receive_registration(data):
    sid = request.sid
    registered_name = data["username"].strip()
    registered_pass = data["password"].strip() 
    print(f'Register attempt: {registered_name} / {registered_pass}')

    # stash into sid into dict to later store in this created users db sid column
    if "sid" not in username_dict:
        username_dict["sid"] = {}
    if sid not in username_dict["sid"]:
        username_dict["sid"][sid] = {}
    # and now we assign these sids to a username, password which is the gotten username and password
    username_dict["sid"][sid]["username"] = registered_name 
    username_dict["sid"][sid]["password"] = registered_pass


    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # i create an sqlite table of users with sid
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        sid TEXT
      )
    """)
    # creating a friends table as well for friend list storage
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS friends (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        friend_name TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
      )
    """)
    # creating a chats table for messages to be stored to those friends
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        friends_name TEXT NOT NULL,
        message TEXT NOT NULL,
        notifications TEXT,
        currently_chatting_with TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
      )
    """)

    # checking if username already exist of register name thats been send to server
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (registered_name,))
    exists = cursor.fetchone()

    if exists:
        # username already exists so we send out to clients specific sid (so that only he would see ant not other users)
        emit("already_exists", "User already exists", to=sid)
    else:
        # else we store the values into the db along with sid
        cursor.execute(
          "INSERT INTO users (username, password, sid) VALUES (?, ?, ?)",
          (
            username_dict["sid"][sid]["username"],
            username_dict["sid"][sid]["password"],
            sid
          )
        )
        conn.commit()
        # success notification
        emit("register_success", f"Registered! Welcome, {registered_name}", to=sid)

    conn.close()




@socketio.on("html_login")
def html_log(login_info):
    sid = request.sid
    # gathering values from client
    login_name = login_info["login_name"]
    login_pass = login_info["login_pass"]
    print(f'Login name: {login_name} Login pass: {login_pass}')

    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (login_name,))
    stored_password = cursor.fetchone()

    if stored_password:
        print(stored_password[2])
        if stored_password[2] == login_pass:
            emit("login_suc", "You've successfully logged in!", to=sid)
            print(f'Login matched!')

            # sending out login name to know in js who sent messages when we open the chat history
            emit("logged_users_name", stored_password[1], to=sid)
            print(f'logged_user_name : {stored_password[1]}')

            # on the login, a new sid is automatically created, therefore i find the username and update to that user sid to a new sid
            sid = request.sid

            cursor.execute("UPDATE users SET sid = ? WHERE username = ?", (sid, login_name))
            conn.commit()
        else:
            emit("login_fail", "Incorrect password.", to=sid)
            print(f'Login failed.')

    else:
        print(f"Username not found.")
        emit("not_found", "User not found.", to=sid)

    # for the console to see
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    

    conn.close()


# on new friend search btn I use sqlite LIKE to send out any similarities of the input to the usernames
@socketio.on("friend_search")
def search(data):
    SID = request.sid
    print(f"friend search: {data}")

    search_inp = data["search_input"]
    who_search = data["whos_searching"]
    # i added whos_searching to make sure i remove it from the list of users that i will send, so that clients wouldnt see their own names in the users

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username LIKE ?", ('%' + search_inp + '%',))
    rows = cursor.fetchall()

    usernames = []
    for row in rows:
        print(row)
        usernames.append(row[1])
    if who_search in usernames:
        usernames.remove(who_search)
    
    emit("emit_rows", usernames, to=SID)

    conn.close()



# receiving from client whether he pressed button (add) to add friend and also sent out that friends name for sql db to properly store that name
@socketio.on("added_friend")
def add_f(data):
    print(f'Added friend: {data}')

    sid = request.sid 

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE sid = ?", (sid,))
    user_row = cursor.fetchone()

    if user_row:
        user_id = user_row[0]

        cursor.execute("SELECT * FROM friends WHERE user_id = ? AND friend_name = ?", (user_id, data))
        existing_friend = cursor.fetchone()

        # if friend is not already added to client friends table, then it adds a new friend
        if not existing_friend:
            cursor.execute("INSERT INTO friends (user_id, friend_name) VALUES (?,?)", (user_id, data))
            conn.commit()

            cursor.execute("SELECT friend_name FROM friends WHERE user_id = ?", (user_id,))
            friends = cursor.fetchall()
            print(f'User friends: {friends}')
            # siunciu, kad pridetas draugas.
            emit("added_friend", "Friend added!", broadcast=True)

        # else i display a message to the client
        else:
            print(f"{data} is already a friend of user {user_id}.")
            emit("already_friend", f'{data} is already in Friend list!', broadcast=True)
    else:
        print('User not found.')

    conn.close()



# sending out the friendlist of current friends the user has.
@socketio.on("requesting_friendlist")
def receive_sendout_friends(data):
    if data:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        sid = request.sid

        cursor.execute("SELECT * FROM users WHERE sid = ?", (sid,))
        user_row = cursor.fetchone()
        friends_list = []


        if user_row:
            cursor.execute("SELECT friend_name FROM friends WHERE user_id = ?", (user_row[0],))
            friends_list = cursor.fetchall()
            
            if len(friends_list) > 0:
                print("Friends found.")
                emit("display_friends", {"friends" : friends_list}, to=sid)

            else:
                print("Friends not found.")

        else:
            print("User not found")


        conn.close()
        print(user_row)
        print(friends_list)



# function for gathering the chat table messages of clients user between him and his friend, whose name i get from js
@socketio.on("request_chat_history")
def handle_chat_history(data):
    if data:
        sid = request.sid
        print(f'friends sid: {data}')
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
    

        # gathering my id
        cursor.execute("SELECT id FROM users WHERE sid = ?", (sid,))
        my_id = cursor.fetchone()

        
        friends_name = data

        # gathering my username based on my sid
        cursor.execute("SELECT username FROM users WHERE sid = ?", (sid,))
        senders_name = cursor.fetchone()

        # now i can gather the messages based on clients user_id and his friends_name
        cursor.execute("SELECT message FROM chats WHERE user_id = ? AND friends_name = ?", (my_id[0], friends_name))
        retreived_messages = cursor.fetchall()

        # I put it all in a list, to send out all messages.
        chat_history = []
        for row in retreived_messages:
            chat_history.append(row[0])
        print(f'chat history: {chat_history}')

        # sending out to client (to="sid")
        emit("msg_from_server", {"senders_name":friends_name, "recipient" : senders_name[0], "message":chat_history}, to=sid)

        # gathering friends sid and sending out to him as well, so that both would receive messages that are currently being sent (auto refresh)
        cursor.execute("SELECT sid FROM users WHERE username = ?", (friends_name,))
        friends_sid = cursor.fetchone()

        emit("msg_from_server", {"senders_name":senders_name[0], "recipient" : friends_name, "message":chat_history}, to=friends_sid[0])

        conn.close()




# function for sending out clients inputs to a certain friend
@socketio.on("sending_msg_js")
def receiving_msg(data):
    print(f'Message: {data["message"]}')
    sid = request.sid

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE sid = ?", (sid,))
    result = cursor.fetchone()

    if result:
        senders_name = result
        print(f'senders_name : {senders_name[0]}')

        received_fr_name = data["sending_to"]
        print(f'friends name: {received_fr_name}')

        cursor.execute("SELECT id FROM users WHERE sid = ?", (sid,))
        my_id = cursor.fetchone()

        # Combining both senders name and messages so that we would see who wrote in the chat history.
        name_and_message = f'{data["sender"]}: {data["message"]}'

        # storing messages to sender's chat log
        cursor.execute("""
            INSERT INTO chats (user_id, friends_name, message) 
            VALUES (?, ?, ?)""", (my_id[0], received_fr_name, name_and_message))
        conn.commit()

        # storing messages to receiver's chat log
        cursor.execute("SELECT id FROM users WHERE username = ?", (received_fr_name,))
        friends_id = cursor.fetchone()

        cursor.execute("SELECT username FROM users WHERE sid = ?", (sid,))
        my_name = cursor.fetchone()

        cursor.execute("""
            INSERT INTO chats (user_id, friends_name, message)
            VALUES (?, ?, ?)""", (friends_id[0], my_name[0], name_and_message))
        conn.commit()

        # notification logic
        cursor.execute("SELECT notifications FROM chats WHERE user_id = ?", (friends_id[0],))
        result = cursor.fetchone()
        notifications = result[0] if result and result[0] else ""

        cursor.execute("SELECT currently_chatting_with FROM chats WHERE user_id = ?", (friends_id[0],))
        currently_chatting = cursor.fetchone()
        currently_chatting = currently_chatting[0] if currently_chatting else None

        if currently_chatting == senders_name[0]:
            print("Notification not sent due to user already being present in the chat.")
        else:
            print("User is currently not chatting with sender.")

            # Split existing notifications or start new list
            seperated_notifications = notifications.split(",") if notifications else []

            if senders_name[0] in seperated_notifications:
                print("Notification from this user is already added")
            else:
                seperated_notifications.append(senders_name[0])
                updated_notifications = ",".join(seperated_notifications)
                print(f'updated notifications: {updated_notifications}')

                cursor.execute("UPDATE chats SET notifications = ? WHERE user_id = ?", (updated_notifications, friends_id[0]))
                conn.commit()
                print("Notification added successfully!")

                cursor.execute("SELECT sid FROM users WHERE id = ?", (friends_id[0],))
                friends_sid = cursor.fetchone()[0]

                emit("notification_update", seperated_notifications, to=friends_sid)
    else:
        print(f'no sid found.')

    conn.close()

        

    




@socketio.on("check_notifications")
def checking_notifics(data):
    if data:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        SID = request.sid
        cursor.execute("SELECT id FROM users WHERE sid = ?", (SID,))
        result = cursor.fetchone()
        if result:
            my_id = result[0]

            cursor.execute("SELECT notifications FROM chats WHERE user_id = ?", (my_id,))
            result2 = cursor.fetchone()
            if result2 and result2[0]:
                notifications = result2[0]
                if notifications:
                    split_notifications = notifications.split(",")
                    print(f'Checking notifications stringed: {notifications}')
                    print(f'Checking notifications splitted: {split_notifications}')
                    # emiting notifications to client
                    emit("notification_update", split_notifications, to=SID) 
                else:
                    print("no current notifications.")
            else:
                print("There are no notifications currently.")
        else:
            print("No id found.")

        conn.close()


@socketio.on("currently_chatting")
def handle_currently(data):
    SID = request.sid
    print(f'received: {data}')

    fixed_data = ''
    for fored_data in data[0]:
        fixed_data = fored_data
    print(fixed_data)

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE sid = ?", (SID,))
        row = cursor.fetchone()
        if not row:
            print("User not found for SID:", SID)
            return
        my_id = row[0]

        # reset & set currently_chatting_with
        cursor.execute("UPDATE chats SET currently_chatting_with = NULL WHERE user_id = ?", (my_id,))
        conn.commit()
        cursor.execute("UPDATE chats SET currently_chatting_with = ? WHERE user_id = ?", (fixed_data, my_id))
        conn.commit()

        # delete that friend from notifications if present
        cursor.execute("SELECT notifications FROM chats WHERE user_id = ?", (my_id,))
        result = cursor.fetchone()
        if result and result[0]:
            split_notifications = result[0].split(",")
            print(f'split_notifications: {split_notifications}')

            if fixed_data in split_notifications:
                split_notifications.remove(fixed_data)
                fixed_string = ",".join(split_notifications)

                cursor.execute(
                    "UPDATE chats SET notifications = ? WHERE user_id = ?",
                    (fixed_string, my_id)
                )
                conn.commit()

                # send the updated list
                cursor.execute("SELECT notifications FROM chats WHERE user_id = ?", (my_id,))
                result2 = cursor.fetchone()

                if result2 and result2[0]:
                    emit("notification_update", result2[0].split(","), to=SID)
                else:
                    print("there are no notifications.")
                    emit("notification_update", [], to=SID)
                    
            else:
                print("This friend hasn't left a notification before. Skipping.")
        else:
            print("no notifications found.")


    finally:
        conn.close()



# if back btn from friends list div was pressed, we also delete from currently_chatting with
@socketio.on("delete_currently")
def delete(data):
    if data:
        SID = request.sid
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE sid = ?", (SID,))
        result = cursor.fetchone()
        if result:
            my_id = result[0]

            cursor.execute("UPDATE chats SET currently_chatting_with = NULL WHERE user_id = ?", (my_id,))
            conn.commit()

            cursor.execute("SELECT notifications FROM chats WHERE user_id = ?", (my_id,))
            result = cursor.fetchone()
            if result and result[0]:
                notifications = result[0]
                split_notifications = notifications.split(",")
                emit("notification_update", split_notifications, to=SID)
            else:
                emit("notification_update", [], to=SID)
            
        else:
            print("ID or SID not found.")

            conn.close()



@socketio.on("search_friends")
def narrow_friends(data):
    if data:
        SID = request.sid
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE sid = ?", (SID,))
        my_id = cursor.fetchone()[0]

        cursor.execute("SELECT friend_name FROM friends WHERE user_id = ? AND friend_name LIKE ?", (my_id, '%' + data + '%'))
        found_friends = cursor.fetchall()
        print(f'found friends: {found_friends}')

        listed_friends = []

        for row in found_friends:
            listed_friends.append(row[0])
        print(f'listed friends: {listed_friends}')

        emit("friends_narrowed", listed_friends, to=SID)
        conn.close()

if __name__ == "__main__":
    socketio.run(web, host="0.0.0.0", port=5000)








