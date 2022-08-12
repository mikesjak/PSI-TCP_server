# By Jakub Mikes

import socket
import threading
import re

# Server messages
SERVER_MOVE = '102 MOVE\a\b'
SERVER_TURN_LEFT = '103 TURN LEFT\a\b'
SERVER_TURN_RIGHT = '104 TURN RIGHT\a\b'
SERVER_PICK_UP = '105 GET MESSAGE\a\b'
SERVER_LOGOUT = '106 LOGOUT\a\b'
SERVER_KEY_REQUEST = '107 KEY REQUEST\a\b'
SERVER_OK = '200 OK\a\b'
SERVER_LOGIN_FAILED = '300 LOGIN FAILED\a\b'
SERVER_SYNTAX_ERROR = '301 SYNTAX ERROR\a\b'
SERVER_LOGIC_ERROR = '302 LOGIC ERROR\a\b'
SERVER_KEY_OUT_OF_RANGE_ERROR = '303 KEY OUT OF RANGE\a\b'

# Client messages
CLIENT_RECHARGING = 'RECHARGING\a\b'
CLIENT_FULL_POWER = 'FULL POWER\a\b'

# Consts
TIMEOUT = 1
RECHARGING_TIMEOUT = 5
SERVER = '192.168.56.1'
HEADER = 256
FORMAT = 'utf-8'
KEYID_PAIRS = [(23019, 32037),
               (32037, 29295),
               (18789, 13603),
               (16443, 29533),
               (18189, 21952)]
RESTRICTIONS = [20, 5, 7, 13, 12, 12, 100, 7]

# Server defining
server = socket.socket()
host = SERVER
port = 1233

# Trying if the address is free
try:
    server.bind((host, port))
except socket.error as e:
    print(str(e))

# =============================================================================================================

# Creates an array of ASCII chars from given string
def ascii_maker(nick):
    ascii_values_of_nick = []
    length = len(nick)

    for character in nick:
        ascii_values_of_nick.append(ord(character))

    if ascii_values_of_nick[length - 1] != 8:
        return False

    elif ascii_values_of_nick[length - 2] != 7:
        return False

    print(f"[ASCII] - {ascii_values_of_nick}")
    return ascii_values_of_nick


# Counts hash from nick and key_id
def get_hash(ascii_nick, key_id, side):
    summary = 0
    for character in ascii_nick:
        summary += character
    user_hash = ((summary - 15) * 1000) % 65536
    user_hash = (user_hash + KEYID_PAIRS[key_id][side]) % 65536
    return user_hash


# Gets the final message
def get_mystery(conn, buffer):
    send_msg(conn, SERVER_PICK_UP)
    message, buffer = get_msg(conn, 6, buffer)
    if message:
        send_msg(conn, SERVER_LOGOUT)
        server_break(conn)
        print(f"[MYSTERY]: {message}")
        return True
    send_error(conn, SERVER_SYNTAX_ERROR)
    server_break(conn)
    return False


# If found returns True
def is_found(x, y):
    if x == 0 and y == 0:
        return True
    return False


# Secures sleeping
def secure_sleeping(conn, msg, buffer):
    if msg == CLIENT_RECHARGING:
        print("[RECHARGING]")
        conn.settimeout(RECHARGING_TIMEOUT)
        print("[WAITING]")
        msg, buffer = get_msg(conn, 6, buffer)
        print(msg)
        if msg != CLIENT_FULL_POWER:
            return False, buffer  # LOGIC ERROR
        return -1, buffer  # ALL GOOD
    return True, buffer  # NOT SLEEPING AT ALL


# Turns off the server
def server_break(conn):
    conn.close()


# Sends normal message
def send_msg(conn, string):
    conn.send(str.encode(string))
    print(f"[SENDING][{string}]")


# Sends error - same as send_msg, just to clarify if it is error or not
def send_error(conn, string):
    conn.send(str.encode(string))
    print(f"[SENDING][{string}]")


# Recieves message and saves it to buffer
def get_msg(conn, position, buffer):
    getting_message = True
    sleep = True
    msg = ''
    text = ''

    # checks if buffer contains message
    if len(buffer) > 0:
        msg = buffer[0]
        msg += '\a\b'
        del buffer[0]
    else:  # buffer is empty
        while getting_message:
            try:
                text = conn.recv(HEADER).decode(FORMAT)
            except socket.error as r:
                print(f"[SOCKER ERROR]:{r}")
                conn.close()
                return False, []
            msg += text
            if text == 'OK -2 -3 \x07\x07\x07\x07\x07\x07\x07\x07\x07':  # Invalid input, didn't know how to fix it
                send_error(conn, SERVER_SYNTAX_ERROR)
                server_break(conn)
                return False, []
            if len(msg) > 1 and msg[len(msg) - 1] == '\b':  # Checks end of message
                break
            if len(msg) == RESTRICTIONS[position] and msg[len(msg) - 1] == '\a':  # To many \a and not a single \b
                print(f"[GOT \A] {msg}")
                send_error(conn, SERVER_SYNTAX_ERROR)
                server_break(conn)
                return False, []

        buffer = msg.split('\a\b')
        msg = buffer[0]
        del buffer[0]
        if len(buffer) >= 1:
            del buffer[-1]
        if msg:
            msg += '\a\b'

    if conn:
        sleep, buffer = secure_sleeping(conn, msg, buffer)
    if sleep == -1:  # SLEPT WELL
        conn.settimeout(TIMEOUT)
        msg, buffer = get_msg(conn, position, buffer)
    elif not sleep:  # DID NOT WAKE UP
        send_error(conn, SERVER_LOGIC_ERROR)
        server_break(conn)
        return False, []
    conn.settimeout(TIMEOUT)
    if len(msg) > RESTRICTIONS[position] and position != 7:
        print("[LENGTH ERROR]")
        send_error(conn, SERVER_SYNTAX_ERROR)
        server_break(conn)
        return False, []
    elif len(msg) > 3 and msg[len(msg) - 3] == ' ':
        send_error(conn, SERVER_SYNTAX_ERROR)
        server_break(conn)
        return -1, []
    return msg, buffer

# Recieves nick and checks syntax errors
def get_nick(conn, buffer):
    nick, buffer = get_msg(conn, 0, buffer)
    if not nick:
        send_error(conn, SERVER_SYNTAX_ERROR)
        server_break(conn)
        return False, []

    ascii_nick = ascii_maker(nick)
    if len(nick) > 20:
        send_error(conn, SERVER_SYNTAX_ERROR)
        server_break(conn)
        return False, []
    if not ascii_nick:
        send_error(conn, SERVER_LOGIN_FAILED)
        server_break(conn)
        return False, []

    return nick, buffer, ascii_nick

# Recieves keyID and checks errors
def get_keyid(conn, buffer):
    key_id, buffer = get_msg(conn, 1, buffer)
    sleep = secure_sleeping(conn, key_id, buffer)

    if not key_id:
        send_error(conn, SERVER_LOGIN_FAILED)
        server_break(conn)
        return -1, []
    if sleep == -1:  # SLEPT WELL
        conn.settimeout(TIMEOUT)
        key_id, buffer = get_msg(conn, 1, buffer)
    elif not sleep:  # DID NOT WAKE UP
        send_error(conn, SERVER_LOGIC_ERROR)
        server_break(conn)
        return -1, []
    if key_id[0].isnumeric():
        key_id = int(key_id[0])
    else:
        send_error(conn, SERVER_SYNTAX_ERROR)  # SERVER_SYNTAX_ERROR
        server_break(conn)
        return -1, []
    if key_id >= 5:
        send_error(conn, SERVER_KEY_OUT_OF_RANGE_ERROR)  # SERVER_KEY_OUT_OF_RANGE_ERROR
        server_break(conn)
        return -1, []

    return key_id, buffer

# Creates hash from nick
def hash_of_nick(conn, ascii_nick, key_id):
    side = 0
    hash_from_nick = get_hash(ascii_nick, key_id, side)
    print(f"[HASH] = {hash_from_nick}")
    server_confirmation = str(hash_from_nick)
    server_confirmation += '\a\b'
    print(f"[HASH-MSG] - {server_confirmation}")
    send_msg(conn, server_confirmation)  # SERVER_CONFIRMATION

# Robot: Turn around!
def send_turn_around(conn, buffer):
    send_msg(conn, SERVER_TURN_LEFT)
    msg, buffer = get_msg(conn, 4, buffer)
    send_msg(conn, SERVER_TURN_LEFT)
    msg, buffer = get_msg(conn, 4, buffer)
    return buffer

# Robot: IS casted when going around obstacle and cross X or Y 
def back_right(conn, x, y, buffer, incidents):
    print("[BACKING RIGHT]")
    send_msg(conn, SERVER_TURN_RIGHT)
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    send_msg(conn, SERVER_TURN_RIGHT)
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    buffer = send_turn_around(conn, buffer)
    if is_found(x, y):
        return True, True, []

    return x, y, buffer

# Robot: IS casted when going around obstacle and cross X or Y 
def back_left(conn, x, y, buffer, incidents):
    print("[BACKING LEFT]")
    send_msg(conn, SERVER_TURN_LEFT)
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    send_msg(conn, SERVER_TURN_LEFT)
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    buffer = send_turn_around(conn, buffer)

    if is_found(x, y):
        return True, True, []

    return x, y, buffer

# Robot: Go around obstacle
def obstacle(conn, x, y, buffer, incidents):
    print("[OBSTACLE] ============================================")
    prev_x = x
    prev_y = y
    send_msg(conn, SERVER_TURN_RIGHT)  # 1
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    send_msg(conn, SERVER_TURN_LEFT)  # 2
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    x_prev = x
    y_prev = y
    send_msg(conn, SERVER_TURN_LEFT)  # 2
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    send_msg(conn, SERVER_TURN_RIGHT)
    msg, buffer = get_msg(conn, 6, buffer)
    if msg:
        x, y = get_coords(msg, conn)
        if is_found(x, y):
            return True, True, []
    if x > 0 and prev_x < 0:
        print(f"[RETURNING]")
        if y < 0:
            x, y, buffer = back_left(conn, x, y, buffer, incidents)
        if y > 0:
            x, y, buffer = back_right(conn, x, y, buffer, incidents)
    elif x < 0 and prev_x > 0:
        print(f"[RETURNING]")
        if y > 0:
            x, y, buffer = back_left(conn, x, y, buffer, incidents)
        if y < 0:
            x, y, buffer = back_right(conn, x, y, buffer, incidents)
    elif y > 0 and prev_y < 0:
        print(f"[RETURNING]")
        if x > 0:
            x, y, buffer = back_left(conn, x, y, buffer, incidents)
        if x < 0:
            x, y, buffer = back_right(conn, x, y, buffer, incidents)
    elif y < 0 and prev_y > 0:
        print(f"[RETURNING]")
        if x > 0:
            x, y, buffer = back_right(conn, x, y, buffer, incidents)
        if x < 0:
            x, y, buffer = back_left(conn, x, y, buffer, incidents)
    print(f"[OBSTACLE END]==============================================")
    return x, y, buffer

# Finds out which direction is the robot heading
# Goes to the nearest axis
def set_direction(conn, x, y, buffer, incidents):
    prev_x = x
    prev_y = y

    x, y, buffer = send_move(conn, x, y, buffer, incidents)
    print(f"{x} vs {prev_x} && {y} vs {prev_y}")
    if x == prev_x:  # sets Y coords to 0
        print("[Y->0]")
        if y < prev_y:
            status = 'DOWN'
            print(status)
            if y >= 0:
                while y != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
            else:  # y < 0
                buffer = send_turn_around(conn, buffer)
                status = 'UP'
                print(status)
                while y != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
        else:  # y > prev_y
            status = 'UP'
            if y <= 0:
                print(status)
                while y != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
            else:  # y > 0
                buffer = send_turn_around(conn, buffer)
                status = 'DOWN'
                print(status)
                while y != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
    else:  # sets X coors to 0
        print("[X->0]")
        if x < prev_x:
            status = 'LEFT'
            if x <= 0:
                buffer = send_turn_around(conn, buffer)
                status = 'RIGHT'
                print(status)
                while x != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
            else:  # x > 0
                print(status)
                while x != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        return False
                return status, buffer, incidents, x, y
        else:  # x > prev_x
            status = 'RIGHT'
            if x < 0:
                print(status)
                while x != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        break
                return status, buffer, incidents, x, y
            else:
                buffer = send_turn_around(conn, buffer)
                status = 'LEFT'
                print(status)
                while x != 0:
                    x, y, buffer = send_move(conn, x, y, buffer, incidents)
                    if is_found(x, y):
                        if get_mystery(conn, buffer):
                            return True
                        break
                return status, buffer, incidents, x, y


def send_move(conn, x, y, buffer, incidents):
    send_msg(conn, SERVER_MOVE)
    msg, buffer = get_msg(conn, 4, buffer)

    if msg:
        prev_x = x
        prev_y = y
        x, y = get_coords(msg, conn)
        if prev_x == x and prev_y == y:
            incidents += 1
            if incidents > 2:
                print("[INCIDENTS]")
                conn.close()
            else:
                x, y, buffer = obstacle(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True, True, []
    else:
        server_break(conn)
        return False, False, []
    if is_found(x, y):
        if get_mystery(conn, buffer):
            return x, y, buffer
        return False, False, []
    return x, y, buffer

# Make robot go to 0, 0
def navigate_stage2(conn, buffer, x, y, incidents, status):
    print(f"X = {x}, Y = {y}")
    if x < 0:
        print("X < 0")
        if status == 'UP':
            send_msg(conn, SERVER_TURN_RIGHT)
            msg, buffer = get_msg(conn, 3, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'DOWN':
            send_msg(conn, SERVER_TURN_LEFT)
            msg, buffer = get_msg(conn, 3, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'LEFT':
            buffer = send_turn_around(conn, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        else:  # status = RIGHT
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
    if x > 0:
        print("X > 0")
        if status == 'UP':
            send_msg(conn, SERVER_TURN_LEFT)
            msg, buffer = get_msg(conn, 3, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'DOWN':
            send_msg(conn, SERVER_TURN_RIGHT)
            msg, buffer = get_msg(conn, 3, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'RIGHT':
            buffer = send_turn_around(conn, buffer)
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        else:  # status == LEFT
            while x != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
    if y < 0:
        print("Y < 0")
        if status == 'RIGHT':
            send_msg(conn, SERVER_TURN_LEFT)
            msg, buffer = get_msg(conn, 3, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'LEFT':
            send_msg(conn, SERVER_TURN_RIGHT)
            msg, buffer = get_msg(conn, 3, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'DOWN':
            buffer = send_turn_around(conn, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        else:  # status = UP
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
    if y > 0:
        print("Y > 0")
        if status == 'RIGHT':
            send_msg(conn, SERVER_TURN_RIGHT)
            msg, buffer = get_msg(conn, 3, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'LEFT':
            send_msg(conn, SERVER_TURN_LEFT)
            msg, buffer = get_msg(conn, 3, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        elif status == 'UP':
            buffer = send_turn_around(conn, buffer)
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True
        else:  # status = DOWN
            while y != 0:
                x, y, buffer = send_move(conn, x, y, buffer, incidents)
                if is_found(x, y):
                    return True

# Navigates the robot
def navigation(conn, buffer, x, y, incidents):
    prev_x = x
    prev_y = y

    x, y, buffer = send_move(conn, 0, 0, buffer, incidents)

    # MEANS X or Y is on 0
    status, buffer, incidents, x, y = set_direction(conn, x, y, buffer, incidents)
    if is_found(x, y):
        return True

    print(f"[STATUS] - {status}")
    if not navigate_stage2(conn, buffer, x, y, incidents, status):
        return False

    return True

# Gets coords from a message
def get_coords(message, conn):
    if message:
        coords = re.findall("[-\d]+", message)
        if len(coords) == 2:
            x = coords[0]
            y = coords[1]
            x = int(x)
            y = int(y)
            print(f"[COORDS] - | {x} | {y} |")
            return x, y
    send_error(conn, SERVER_SYNTAX_ERROR)
    server_break(conn)
    return -101, 100

# Handles a single client
def handle_client(conn, addr, count):
    print(f"[{count}][NEW CONNECTION] - {addr}")

    conn.settimeout(TIMEOUT)
    buffer = []
    incidents = 0

    while True:
        #  NICK
        nick, buffer, ascii_nick = get_nick(conn, buffer)
        if not nick:
            return False
        print(f"[{count}][NICK] - {nick}")

        # KEYID
        send_msg(conn, SERVER_KEY_REQUEST)  # WANTING KEYID
        key_id, buffer = get_keyid(conn, buffer)
        if key_id == -1:
            return False
        print(f"[{count}][KEYID] - {key_id}")

        # HASH FROM NICK
        hash_of_nick(conn, ascii_nick, key_id)

        # CHECKING HASHES
        client_hash, buffer = get_msg(conn, 7, buffer)
        client_hash = client_hash[:-2]
        side = 1
        hash_check = get_hash(ascii_nick, key_id, side)
        hash_check = str(hash_check)

        if not client_hash:
            return False
        for char in client_hash:  # CHECKING IF HASH IS A NUMBER
            if not char.isdecimal():
                print(char)
                send_error(conn, SERVER_SYNTAX_ERROR)
                server_break(conn)
                return False

        # ascii_maker(client_hash)
        # ascii_maker(hash_check)

        print(f"[{count}][HASH-CHECK] - {client_hash} vd {hash_check}")
        if hash_check != client_hash:
            if len(client_hash) > 5:
                send_error(conn, SERVER_SYNTAX_ERROR)
                server_break(conn)
                return False
            else:
                send_error(conn, SERVER_LOGIN_FAILED)
                print(f"[ERROR] - HASHES DO NOT MATCH")
                server_break(conn)
                return False

        send_msg(conn, SERVER_OK)
        # END OF AUTHENTICATION

        # NAVIGATION
        send_msg(conn, SERVER_MOVE)
        msg, buffer = get_msg(conn, 3, buffer)
        if not msg:
            print(f"[ERROR] TOO LONG")
            return False
        x, y = get_coords(msg, conn)
        if x == -101 and y == 100:
            print(f"[{count}][BAD-COORDS]")
            return False
        if is_found(x, y):
            get_mystery(conn, buffer)
            return True

        navigate = navigation(conn, buffer, x, y, incidents)

        if not navigate:
            return False
        break

    return True

# Infinite loop, creates threads
def start():
    server.listen()
    print(f"[LISTENING] on {SERVER}:{port}")
    count = 0
    while True:
        count += 1
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, count))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] - {threading.active_count() - 1}")


print("[STARTING] Server is starting...")
start()
server.close()
