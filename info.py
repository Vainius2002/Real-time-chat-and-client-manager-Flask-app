from flask import Flask, request, render_template, send_from_directory
from flask_socketio import emit, SocketIO
import sqlite3
import os
# importing secure filename for as the name says, securing filenames
from werkzeug.utils import secure_filename
# importing jsonfiy cause i need to return something in method"post" route functions in order to not get an error
from flask import jsonify


web = Flask(__name__)
socketio = SocketIO(web)  # initialize SocketIO

# Set up the upload folder with path to my pcs certain path
UPLOAD_FOLDER = r"C:/Users/Lenovo/Desktop/python/flasks app/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
web.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



conn = sqlite3.connect("prisijungimai.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS prisijungimai (id INTEGER PRIMARY KEY, vardas TEXT, slaptazodis TEXT, filename2 file)")
conn.commit()
conn.close()
print("sukurta prisijungimai.")

cursor.execute("INSERT INTO prisijungimai (vardas, slaptazodis) VALUES (?, ?)", ("admin", "123"))
conn.commit()
conn.close()

# conn = sqlite3.connect("klientai.db")
# cursor = conn.cursor()
# cursor.execute("DELETE FROM klientai")
# conn.commit()
# conn.close()


conn = sqlite3.connect("klientai.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS klientai (
    id INTEGER PRIMARY KEY,
    vardas TEXT,
    pavarde TEXT,
    imone TEXT,
    adresas TEXT,
    pastabos TEXT,
    filename TEXT
)
""")
conn.commit()
conn.close()
print("database created")






# receives from client (js) username and password inputs to store check whether it already exists in a db
@socketio.on("check_login")
def checking_login(data):
    SID = request.sid
    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("prisijungimai.db")
    cursor = conn.cursor()

    cursor.execute("SELECT vardas FROM prisijungimai WHERE vardas = ? AND slaptazodis = ?", (username, password))
    result = cursor.fetchone()

    # emiting results to client
    if result:
        print(f"Sekmingai prisijungėte!")
        emit("login_success", {"msg": "Sėkmingai prisijungėte!", "name" : username}, to=SID)
    else:
        print("login failed.")
        emit("login_failed", "Nepavyko prisijungti.", to=SID)

    conn.close()


# updating sid on the login in the database since it changes after logging in again
@socketio.on("update_sid")
def updating_sid(data):
    if data:
        SID = request.sid
        username = data["login_username"]

        conn = sqlite3.connect("prisijungimai.db")
        cursor = conn.cursor()

        cursor.execute("UPDATE prisijungimai SET sid = ? WHERE vardas = ?", (SID, username))
        conn.commit()
        conn.close()




@web.route("/")
def hello():
    return render_template("info.html")


# once client sends out on button click (find clients btn), server gets clients using LIKE and sends out back to the sid
@socketio.on("find_clients")
def finding_clients(data):
    if data:
        SID = request.sid
        klientu_input = data["klientu_search"]


        conn = sqlite3.connect("klientai.db")
        cursor = conn.cursor()

        search_pattern = f"%{klientu_input}%"
        cursor.execute("""
            SELECT vardas, pavarde, imone FROM klientai 
            WHERE vardas LIKE ? OR pavarde LIKE ? OR imone LIKE ?
        """, (search_pattern, search_pattern, search_pattern))

        klientai = cursor.fetchall()

        clients = []

        for row in klientai:
            clients.append(row)
        print(clients)

        emit("clients_found", clients, to=SID)







# handling file uploads (images) once client savs a form with a butonclick
@web.route("/uploads", methods=["POST"])
def upload():
    vardas = request.form.get("vardas")
    pavarde = request.form.get("pavarde")
    imone = request.form.get("imone")
    adresas = request.form.get("adresas")
    pastabos = request.form.get("pastabos")

    # since i allowed more than one picture, i getlist, instead of get
    files = request.files.getlist("nuotrauka")


    conn = sqlite3.connect("klientai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM klientai WHERE vardas = ? AND pavarde = ?", (vardas, pavarde))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        # returning reports
        return 'Vardas ir pavarde jau sukurta.', 400
        
    # creating a list to store saved filenames of pictures
    saved_filenames = []
    if vardas and pavarde != '':
        # Create folder per person with created persons name and lastname
        folder_name = f"{vardas}_{pavarde}".replace(" ", "_")
        folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
        # if folder doesnt exist it creates a new one in my path
        os.makedirs(folder_path, exist_ok=True)

        # since file is a list i loop
        for file in files:
            # insert int oa secure filename
            filename = secure_filename(file.filename)
            # save the file
            file_path = os.path.join(folder_path, filename)
            file.save(file_path)
            saved_filenames.append(f'{folder_name}/{filename}')
        # i append it as a string joined with commas
        pictures_str = ','.join(saved_filenames)
    else:
        # returning reports
        return "Įterpkite vardą bei pavardę", 400


    # saving info in db
    cursor.execute("""
        INSERT INTO klientai (vardas, pavarde, imone, adresas, pastabos, filename)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (vardas, pavarde, imone, adresas, pastabos, pictures_str))
    conn.commit()
    conn.close()

    return "Sekmingai išsaugota!", 200
    
    

# once a see customer btn is clicked, server handles the logic of sending out customers table information to the client(sid)
@socketio.on("see_client")
def seeing_client(data):
    SID = request.sid
    clicked_client_v = data["name"][0]
    clicked_client_p = data["name"][1]
    print(f'received {clicked_client_v}, {clicked_client_p}')

    conn = sqlite3.connect("klientai.db")
    cursor = conn.cursor()

    cursor.execute("SELECT vardas, pavarde, imone, adresas, pastabos FROM klientai WHERE vardas = ? AND pavarde = ?", (clicked_client_v, clicked_client_p))
    row = cursor.fetchone()
    # i store descriptions as well (vardas : Jonas, pavarde : kazlauskas)
    column_names = [desc[0] for desc in cursor.description]

    if not row:
        emit("klientas", {"error": "Client not found"}, to=SID)
        return

    kliento_info = list(zip(column_names, row))

    # getting picture names from filename column
    cursor.execute("SELECT filename FROM klientai WHERE vardas = ? AND pavarde = ?", (clicked_client_v, clicked_client_p))
    filenames = cursor.fetchall()
    print(f'filenames before: {filenames}')

    listed_pics = []
    for pictures in filenames:
        pics_split = pictures[0].split(",")
        for pic in pics_split:
            listed_pics.append(pic.strip())
    # i send out picture names as a string thats split with commas so that i would then get them seperated in js and displayed in img element
    print(f'fotkes: {listed_pics}')

    conn.close()

    # I emit full info of customer without pictures
    emit("klientas", {
        "kliento_info": kliento_info,
        "client_v": clicked_client_v,
        "client_p": clicked_client_p,
        "pic_names" : listed_pics
    }, to=SID)




# listening for js Išštrinti btn to be clicked and applying delete logic from both os and filename column in that customers db
@socketio.on("delete_pic")
def deleting(data):
    picture_name = data["delete"]
    client_name = data["client_name"]
    client_lastname = data["client_lastname"]

    conn = sqlite3.connect("klientai.db")
    cursor = conn.cursor()

    # Select current filenames
    cursor.execute("SELECT filename FROM klientai WHERE vardas = ? AND pavarde = ?", (client_name, client_lastname))
    filename_list = cursor.fetchall()
    print(f'filename: {filename_list}')

    listed_filenames = []
    if filename_list and filename_list[0][0]:
        listed_filenames = filename_list[0][0].split(",")
    print(f'split string: {listed_filenames}')

    if picture_name in listed_filenames:
        listed_filenames.remove(picture_name)

        full_path = os.path.join(web.config["UPLOAD_FOLDER"], picture_name)
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"Deleted file from disk: {full_path}")
        else:
            print(f"File not found on disk: {full_path}")

    print(f'selected picture name: {picture_name}')
    print(f'corrected_filenames: {listed_filenames}')

    update_into_string = ",".join(listed_filenames)
    cursor.execute("UPDATE klientai SET filename = ? WHERE vardas = ? AND pavarde = ?", (update_into_string, client_name, client_lastname))
    conn.commit()
    conn.close()




# listening to apply logic about changing certain input from js
@socketio.on("change_input")
def edit_input(data):
    edited_input = data["input_value"].strip()
    client_name = data["client_name"].strip()
    client_lastname = data["client_lastname"].strip()
    into_whats_changed = data["whats_changed"]  
    # i get description of whats being changed to make sure i can actually find the previous db i changed (edited) and then i update the new value
    

    # receiving previous names if there were any changes to them so that i could store new names and lastnames in the db.
    old_name = data["old_name"]
    old_lastname = data["old_lastname"]
    # i receive input that i need to change to, i receive who sent to make sure i update right sqlite customer table, and i also get a description
    # of what the input should change, to make sure that if description will be vardas or pavarde, i would also change the os of that folder
    # so that next time i would find pictures in the folder and be able to display them because the path is renewed.

    print(f'Ka nori pakeist {into_whats_changed}')
    print(f'I ka nori pakeist {edited_input}')

    conn = sqlite3.connect("klientai.db")
    cursor = conn.cursor()


    # building old folder path based on current DB data
    old_folder_name = f"{old_name}_{old_lastname}".replace(" ", "_")
    old_path = os.path.join(UPLOAD_FOLDER, old_folder_name)

    # building new folder name depending on what changed
    if into_whats_changed == "vardas":
        new_folder_name = f"{edited_input}_{old_lastname}".replace(" ", "_")
    elif into_whats_changed == "pavarde":
        new_folder_name = f"{old_name}_{edited_input}".replace(" ", "_")
    else:
        new_folder_name = old_folder_name

    new_path = os.path.join(UPLOAD_FOLDER, new_folder_name)

    # renaming folder if needed
    if into_whats_changed in ["vardas", "pavarde"]:
        if os.path.exists(old_path):
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                print(f'renamed old path {old_path}, into new {new_path}')
            else:
                print("new folder path already exists")
        else:
            print("couldnt find old folder")

    # updating db of the client whether his name or lastname has been changed
    sql = f"UPDATE klientai SET {into_whats_changed} = ? WHERE vardas = ? AND pavarde = ?"
    cursor.execute(sql, (edited_input, old_name, old_lastname))
    conn.commit()

    print("database updated")
    # and i also change the filename of the client because, i store images as client_name_lastname/img name so if name of client has been changed
    # i then also change the filename in sqlite based on new name and lastname
    cursor.execute("SELECT filename FROM klientai WHERE vardas = ? AND pavarde = ?", (client_name, client_lastname))
    filenames = cursor.fetchone()
    if filenames and filenames[0]:
        stringed_filenames = filenames[0]
        
        edited_file_string = stringed_filenames.replace(old_folder_name + "/", new_folder_name + "/")
        
        cursor.execute(
            "UPDATE klientai SET filename = ? WHERE vardas = ? AND pavarde = ?",
            (edited_file_string, client_name, client_lastname)
        )
        conn.commit()
        print(f"`filename` column updated from: {stringed_filenames} to: {edited_file_string}")
    else:
        print("No filenames to update")

    conn.close()




# logic for when a person wants to edit a customer and only then add pictures (so its receiving a new form basially with an image file)
@web.route("/upload_images", methods=["POST"])
def new_upload():
    # getting form data
    vardas = request.form.get("vardas")
    pavarde = request.form.get("pavarde")
    
    # getting uploaded files list
    nuotraukos = request.files.getlist("images")
    
    # preparing folder name and path for storing files
    folder_name = f"{vardas}_{pavarde}".replace(" ", "_")
    folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
    
    # ensuring the folder exists but create if it doesnt
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # building a list of filenames for saving to DB
    pic_name_list = []
    for file in nuotraukos:
        # checking if filename is empty (no file selected)
        if file.filename == "":
            return "Nuotraukos nepasirinktos", 400
        
        # ensuring file is safe
        safe_filename = secure_filename(file.filename)
        
        filename_with_path = f"{folder_name}/{safe_filename}"
        
        pic_name_list.append(filename_with_path)
    
    # joining the new filenames with old ones via comma to make sure logic stays the same
    new_filenames_str = ",".join(pic_name_list)
    
    # connect to database
    conn = sqlite3.connect("klientai.db")
    cursor = conn.cursor()
    
    # get existing filenames string
    cursor.execute(
        "SELECT filename FROM klientai WHERE vardas = ? AND pavarde = ?",
        (vardas, pavarde)
    )
    result = cursor.fetchone()
    
    if result is not None and result[0] is not None:
        # only storing filenames in a different var if filename is not empty
        existing_filenames_str = result[0]
    else:
        existing_filenames_str = ""
    
    # combine old and new filenames strings with comma so that my filename style would stay the same (string seperated by commas)
    if existing_filenames_str != "":
        updated_filenames_str = existing_filenames_str + "," + new_filenames_str
    else:
        updated_filenames_str = new_filenames_str
    
    # update database with the edited filenames string due to one more file or files
    if updated_filenames_str != "":
        cursor.execute(
            "UPDATE klientai SET filename = ? WHERE vardas = ? AND pavarde = ?",
            (updated_filenames_str, vardas, pavarde)
        )
        conn.commit()
    
    # save the files to disk inside the folder as well
    for file in nuotraukos:
        safe_filename = secure_filename(file.filename)
        file_path = os.path.join(folder_path, safe_filename)
        
        # save the uploaded file
        file.save(file_path)
    
    conn.close()
    
    # return response to not get an error since some return is needed
    return jsonify({
        "status": "success"
    })



@web.route("/uploads/<path:filename>")
def serve_file(filename):
    return send_from_directory(web.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    socketio.run(web, debug=True)



# sunkiausia dalis viskas kas susije su os kadangi reik dar mokintis apie library 144 eil.
# bei stipriai strigau kol nesupratau return jsonify virs manes, nes nezinojau kodel gaudavau error, o pasirodo turi buti kazkoks return