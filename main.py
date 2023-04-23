from flask import Flask, send_from_directory, send_file, request, render_template
from flask_socketio import SocketIO
from gevent import monkey
from gevent.pywsgi import WSGIServer
from stupidArtnet import StupidArtnetServer
from geventwebsocket.handler import WebSocketHandler
from time import sleep

monkey.patch_all()

app = Flask(__name__)
socketio = SocketIO(app)

prev_data = []
connectedUsers = {}  # Skal mappe socketID-er med setenummer, radnummer og felt
amountOfSeats = 10
amountOfRows = 10

@app.route('/farge')
def farge():
    return send_file('websocket.html')

@app.route("/")
def home():
    return render_template("hjem.html", amountOfRows=amountOfRows, amountOfSeats=amountOfSeats)

#Route for å implementere statiske filer til hjemskjerm. Dvs. MGP-bilde
@app.route('/static/<path:path>')
def getStaticFile(path):
    return send_from_directory("static", path) 

def getRGBString(data):  # Convert list of size 3 to rgb-string
    return ("#" + 3 * "{:02x}").format(*data)

def posToIndex(rowNumber, seatNumber):  # Find correct index in unicast-list from rownumber and seatnumber
    return 3*((amountOfRows - rowNumber) * amountOfSeats + seatNumber - 1)

# MODES

waiting_time=0.1

# def wave(color1, color2):
#     color=""
#     for i in range(amountOfSeats):
#         for id, pos in connectedUsers.items():
#             if pos["sete"]==i:
#                 color=color1
#             else:
#                 color=color2
#             socketio.emit("update:color", color, room=id)
#         sleep(waiting_time)

def default(data):
    for id, pos in connectedUsers.items():  # Iterate over each user
        try:
            index = posToIndex(pos["rad"], pos["sete"])
            # if prev_data[index:index+3] == data[index:index+3]:
            #     continue
            color = getRGBString(data[index: index+3])
            socketio.emit("update:color", color, room=id)
        except IndexError:
            print(f"IndexError: Seat {pos} doesn't exist")
        except Exception:
            print(f"Sending failed for user {id} at position {pos}")

prev_data = []

@socketio.on('update:color')  # Function called when new data is received
def send_data(data):
    global prev_data
    if len(connectedUsers)==0:
        return
    # if 0<data[-1]:
    #     wave(getRGBString(data[:3]), getRGBString(data[3:6]))
    default(data)
    prev_data = data

@socketio.on('build:addUser')  # Function called when new user connects to websocket (see websocket.html)
def add_user(radNummer, seteNummer):
    try:
        print("A user connected to the websocket-server")
        radNummer = int(radNummer)
        seteNummer = int(seteNummer)
        connectedUsers[request.sid] = {"rad": radNummer, "sete": seteNummer}  # User added to doctionary
        print(connectedUsers)
        print(f"Amount of people connected: {len(connectedUsers)}")
    except Exception:
        print("Failed to add user")

@socketio.on("disconnect")  # Function called when user disconnects (e.g closes browser)
def remove_user():
    # del connectedUsers[request.sid]
    print("User removed")

artnet_server = StupidArtnetServer()
listener = artnet_server.register_listener(universe=0, callback_function=send_data)

if __name__ == "__main__":
    http_server = WSGIServer(('', 8000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()