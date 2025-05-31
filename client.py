import socket

#UDPソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = input("Type in the server's address to connect to: ")
server_port = 9001

#送信元である自身のアドレスを設定
address = '' #空の文字列も0.0.0.0と同じ
port = 9050

user_name = input("Type in your name: ")
user_name_bytes = user_name.encode('utf-8') #ユーザー名をバイト列に変換（UTF-8 という文字コードで文字列をエンコード（変換）)
usernamelen = len(user_name_bytes)  # バイト長

# if usernamelen > 255:
#     raise ValueError("Username too long. Must be 255 bytes or less.")

message_body = input("Type your message: ")
message_bytes = message_body.encode('utf-8') #メッセージ本文をバイト列に変換 ※ネットワーク通信では、文字列はそのまま送れない

# プロトコル形式でデータ作成
#bytes([usernamelen]) は、その整数を 1バイトのバイト列 に変換するためのコード
message = bytes([usernamelen]) + user_name_bytes + message_bytes

#ソケットに自身のアドレスをバインド
sock.bind((address,port))

try:
  print('sending from {}: {}'.format(user_name, message_body))
  # サーバへのデータ送信
  sent = sock.sendto(message, (server_address, server_port))
  print('Send {} bytes'.format(sent))
  
  # 応答を受信
  print('waiting to receive')
  data, server = sock.recvfrom(4096)
  usernamelen = data[0]
  username = data[1:1+usernamelen].decode('utf-8') #ユーザー名を復元
  message = data[1+usernamelen:].decode('utf-8') #メッセージ本文を復元
  print(f"From {username}@{server}: {message}")

finally:
  print('closing socket')
  sock.close()