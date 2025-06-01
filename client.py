import socket
import threading

#UDPソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#サーバ情報
server_address = input("Type in the server's address to connect to: ")
server_port = 9001

#送信元である自身のアドレスを設定
# address = '' #空の文字列も0.0.0.0と同じ
# port = 9050

#ユーザー情報入力
user_name = input("Type in your name: ")
user_name_bytes = user_name.encode('utf-8') #ユーザー名をバイト列に変換（UTF-8 という文字コードで文字列をエンコード（変換）)
usernamelen = len(user_name_bytes)  # バイト長

if usernamelen > 255:
    raise ValueError("Username too long. Must be 255 bytes or less.")

# === 受信用スレッド ===
def receive_messages():
    while True:
        try:
            data, server = sock.recvfrom(4096)
            usernamelen = data[0]
            username = data[1:1+usernamelen].decode('utf-8')
            message = data[1+usernamelen:].decode('utf-8')
            print(f"\nFrom {username}@{server}: {message}")
        except Exception as e:
            print("Receive error:", e)
            break

# スレッドを起動
recv_thread = threading.Thread(target=receive_messages, daemon=True)
recv_thread.start()

#ソケットに自身のアドレスをバインド←OSに任せるならbindは不要。というより設定するとポート重複が起きてしまう
# sock.bind((address,port))


# === メッセージ送信ループ ===
try:
    while True:
        message_body = input("Type your message: ")
        if message_body.lower() in ['exit', 'quit']:
            break
        message_bytes = message_body.encode('utf-8') #メッセージ本文をバイト列に変換 ※ネットワーク通信では、文字列はそのまま送れない
        # プロトコル形式でデータ作成
        #bytes([usernamelen]) は、その整数を 1バイトのバイト列 に変換するためのコード
        message = bytes([usernamelen]) + user_name_bytes + message_bytes
        print('sending from {}: {}'.format(user_name, message_body))
        # サーバへのデータ送信
        sent = sock.sendto(message, (server_address, server_port))
        print('Send {} bytes'.format(sent))
  
finally:
  print('closing socket')
  sock.close()