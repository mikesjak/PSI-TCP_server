# Authentication testing client
# By Jakub Mikes

import socket

HEADER = 64
PORT = 1233
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = '127.0.0.0'
ADDR = (SERVER, PORT)

KEYID_PAIRS = [(23019, 32037),
               (32037, 29295),
               (18789, 13603),
               (16443, 29533),
               (18189, 21952)]

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

def get_hash(ascii_nick, key_id, side):
    sum = 0
    for character in ascii_nick:
        sum += character
    user_hash = ((sum - 15) * 1000) % 65536
    print(KEYID_PAIRS[key_id][side])
    user_hash = (user_hash + KEYID_PAIRS[key_id][side]) % 65536
    return user_hash

def ascii_maker(nick):
    ascii_values_of_nick = []
    for character in nick:
        ascii_values_of_nick.append(ord(character))
    print(f"[ASCII] - {ascii_values_of_nick}")
    return ascii_values_of_nick

def send(msg):
    message = msg.encode(FORMAT)
    key_id = "1\a\b"
    client.send(message)
    print(client.recv(2048).decode(FORMAT))

    client.send(key_id.encode(FORMAT))
    print(client.recv(2048).decode(FORMAT))

    ascii_nick = ascii_maker(msg)
    key_id = int(key_id[0])
    side = 1
    hash = get_hash(ascii_nick, key_id, side)
    hash = str(hash) + '\a\b'
    client.send(hash.encode(FORMAT))
    print(client.recv(2048).decode(FORMAT))

send("Mnau!\a\b")
