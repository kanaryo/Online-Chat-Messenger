import socket
import sys
import os
import threading

def protocol_header(filename_length, json_length, data_length):
    return filename_length.to_bytes(1, "big") + json_length.to_bytes(3,"big") + data_length.to_bytes(4,"big")

#IPv4,TCPを指定してソケットを作成
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# サーバが待ち受けているポートにソケットを接続します
server_address = input("Type in the server's address to connect to: ")
tcp_server_port = 9001

print('connecting to {}'.format(server_address, tcp_server_port))

try:
    tcp_sock.connect((server_address, tcp_server_port))
except socket.error as err:
    print(err)
    sys.exit(1)
    
# === 受信用スレッド ===
def receive_messages():
    while True:
        try:
            data, server = udp_sock.recvfrom(4096)
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

try:
    # 操作選択（1: ルーム作成, 2: ルーム参加）
    while True:
        operation_input = input("操作を選んでください（1: ルーム作成, 2: ルーム参加）: ")
        if operation_input in ("1", "2"):
            operation = int(operation_input)
            break
        else:
            print("1 または 2 を入力してください。")
    roomname = input("チャットルーム名を入力してください: ")
    username = input("ユーザー名を入力してください: ")
    state = 0       # 初期状態
    
    # バイト列に変換
    roomname_bytes = roomname.encode('utf-8')
    username_bytes = username.encode('utf-8')
    
    roomname_size = len(roomname_bytes) #バイト列のバイト数をカウント
    operation_payload_size = len(username_bytes)

    #ヘッダー作成
    header = (
        roomname_size.to_bytes(1, 'big') +
        operation.to_bytes(1, 'big') +
        state.to_bytes(1, 'big') +
        operation_payload_size.to_bytes(29, 'big')
    )
    
    # ヘッダー送信
    tcp_sock.sendall(header)
    
    # ボディ送信 (roomname + operation_payload)
    tcp_sock.sendall(roomname_bytes + username_bytes)

    # --- サーバーからのレスポンス受信 ---
    
    # まずレスポンスヘッダーを受信（32バイト）
    resp_header = b''
    while len(resp_header) < 32:
        chunk = tcp_sock.recv(32 - len(resp_header))
        if not chunk:
            raise ConnectionError("サーバーとの接続が切断されました")
        resp_header += chunk
    
    # レスポンスヘッダーの解析
    resp_roomname_size = resp_header[0]
    resp_operation = resp_header[1]
    resp_state = resp_header[2]
    resp_body_size = int.from_bytes(resp_header[3:32], 'big')
    
    # レスポンスボディ受信
    resp_body = b''
    while len(resp_body) < resp_body_size:
        chunk = tcp_sock.recv(resp_body_size - len(resp_body))
        if not chunk:
            raise ConnectionError("サーバーとの接続が切断されました")
        resp_body += chunk
    
    print(f"レスポンス受信: operation={resp_operation}, state={resp_state}, body={resp_body}")
    
    # State=1 (ステータス応答) の場合
    if resp_state == 1:
        status_code = resp_body[0]
        if status_code != 0:
            print("処理失敗、終了します。")
        else:
            print("処理成功、トークンを待ちます。")

        # 成功ならState=2のトークン送信を待つ
        if status_code == 0:
            # 2回目のレスポンスヘッダー受信
            resp_header2 = b''
            while len(resp_header2) < 32:
                chunk = tcp_sock.recv(32 - len(resp_header2))
                if not chunk:
                    raise ConnectionError("サーバーとの接続が切断されました")
                resp_header2 += chunk

            resp_state2 = resp_header2[2]
            resp_body_size2 = int.from_bytes(resp_header2[3:32], 'big')

            # 2回目のレスポンスボディ受信（トークン）
            resp_body2 = b''
            while len(resp_body2) < resp_body_size2:
                chunk = tcp_sock.recv(resp_body_size2 - len(resp_body2))
                if not chunk:
                    raise ConnectionError("サーバーとの接続が切断されました")
                resp_body2 += chunk
            
            token = resp_body2
            print(f"受信したトークン: {token}")

    # メッセージ送信処理
    user_name_bytes = username.encode('utf-8') #ユーザー名をバイト列に変換（UTF-8 という文字コードで文字列をエンコード（変換）)
    usernamelen = len(user_name_bytes)  # バイト長
    
    while True:
        #メッセージ本文作成
        message_body = input("Type your message: ")
        if message_body.lower() in ['exit', 'quit']:
            break
        
        #ヘッダー作成
        roomname_bytes = roomname.encode('utf-8')
        
        roomname_size = len(roomname_bytes)
        token_size = len(token)
        
        chat_header = (
            roomname_size.to_bytes(1, 'big') +
            token_size.to_bytes(1, 'big')
        )
        
        #ボディ作成
        message_bytes = message_body.encode('utf-8') #メッセージ本文をバイト列に変換 ※ネットワーク通信では、文字列はそのまま送れない

        message = (
            roomname_bytes + 
            token + 
            message_bytes
        )
        udp_server_port = 9002
        # UDPは送信先を毎回指定する必要があるので
        # ヘッダーとメッセージをまとめて一回で送る
        packet = chat_header + message
        print('sending from {}: {}'.format(username, message_body))
        sent = udp_sock.sendto(packet, (server_address, udp_server_port))

        # # ヘッダー送信
        # udp_sock.sendall(chat_header)
        
        # # ボディ送信
        # sent = udp_sock.sendto(message, (server_address, server_port))
        print('Send {} bytes'.format(sent))
    
except Exception as e:
    print(f"エラー: {e}")

finally:
    print('closing socket')
    tcp_sock.close()