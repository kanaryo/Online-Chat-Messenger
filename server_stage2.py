from datetime import datetime, timedelta
import socket
import os
from pathlib import Path
import uuid
import threading

def generate_token():
    return uuid.uuid4().hex.encode('utf-8')[:255]  # 最大255バイト

#TCPのチャットルーム作成・参加処理
def tcp_server():
    #IPv4,TCPを指定してソケットを作成
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #任意のIPアドレスからの接続を受け入れる
    server_address = '0.0.0.0'
    tcp_server_port = 9001

    #ソケットをサーバのアドレスとポートに紐付けします。
    tcp_sock.bind((server_address, tcp_server_port))

    # サーバは一度に最大1つの接続を受け入れる
    tcp_sock.listen(1)

    rooms = {}  # ルーム名 → トークンマップ

    while True:
        connection, client_address = tcp_sock.accept()
        try:
            print('connection from', client_address)
            #ヘッダーの読み取り
            header = connection.recv(32)

            roomname_size = int.from_bytes(header[:1], "big")
            
            #操作コード（チャットルーム作成or参加）
            operation = int.from_bytes(header[1:2], "big")
            #ステータスコード（そのアクションの進行状況）
            state = int.from_bytes(header[2:3], "big")
            operation_payload_size = int.from_bytes(header[3:32], "big")
            
            #受信すべきボディの総バイト数
            body_size = roomname_size + operation_payload_size
            
            #ボディの初期化
            body = b""
            
            
            #必要なサイズ（body_size）に達するまで受信を繰り返す
            while len(body) < body_size:
                chunk = connection.recv(body_size - len(body))
                
                if not chunk:
                    raise ConnectionError("接続が中断されました")
                
                body += chunk
                
            # ボディの分割
            #ルーム名
            roomname_bytes = body[:roomname_size]
            #ユーザ名
            operation_payload_bytes = body[roomname_size:]
            
            #RoomNamesをUTF-8でデコード
            roomname = roomname_bytes.decode("utf-8")
            username = operation_payload_bytes.decode('utf-8')

            if operation == 1 and state == 0:
                print(f"新しいチャットルーム作成要求: room={roomname}, user={username}")

                # Room作成処理
                if roomname in rooms:
                    # ステータスコード: 1 = 失敗（すでに存在）
                    response = b'\x01'
                else:
                    token = generate_token()
                    rooms[roomname] = {'token': token}
                    # ステータスコード: 0 = 成功
                    response = b'\x00'
            
                # リクエストの応答、ステータス応答（State=1）
                resp_header = bytes([roomname_size, operation, 1]) + len(response).to_bytes(29, 'big')
                connection.send(resp_header + response)
            
                if response == b'\x00':
                    # リクエストの完了、トークン送信（State=2）
                    token_bytes = token
                    resp_header = bytes([roomname_size, operation, 2]) + len(token_bytes).to_bytes(29, 'big')
                    connection.send(resp_header + token_bytes)
                    
            elif operation == 2 and state == 0: # チャットルーム参加
                print(f"チャットルーム参加要求: room={roomname}, user={username}")
                
                # ルームが存在しなければエラー
                if roomname not in rooms:
                    # ルーム存在しない → リクエストの応答、ステータス応答（State=1）
                    response = b'\x01'
                    resp_header = bytes([roomname_size, operation, 1]) + len(response).to_bytes(29, 'big')
                    connection.send(resp_header + response)
                    continue
                
                # 参加トークンを生成
                participant_token = generate_token()

                # サーバー側の部屋情報に参加者トークンを記録（必要に応じて構造を拡張）
                if 'participants' not in rooms[roomname]:
                    rooms[roomname]['participants'] = []
                    
                rooms[roomname]['participants'].append({
                    'username': username,
                    'token': participant_token
                })

                # IPアドレスのマッピングを辞書形式で保持
                if 'token_ip_map' not in rooms[roomname]:
                    rooms[roomname]['token_ip_map'] = {}

                rooms[roomname]['token_ip_map'][participant_token] = client_address[0]

                # リクエストの応答、ステータス応答（State=1）
                response = b'\x00'
                resp_header = bytes([roomname_size, operation, 1]) + len(response).to_bytes(29, 'big')
                connection.send(resp_header + response)

                # リクエストの完了、トークン送信（State=2）
                resp_header = bytes([roomname_size, operation, 2]) + len(participant_token).to_bytes(29, 'big')
                connection.send(resp_header + participant_token)
                
        except Exception as e:
            print(f"エラーが発生しました: {e}")
        
        finally:
            print(f"接続を終了します: {client_address}")
            connection.close()
        
        pass
    
#UDPでチャットメッセージを送受信する処理
def udp_server():
    # AF_INETを使用し、UDPソケットを作成
    udp_sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_address = '0.0.0.0'
    #ポート9001で待ち受ける。
    udp_server_port = 9002
    print('starting up on port {}'.format(udp_server_port))

    # ソケットを特殊なアドレス0.0.0.0とポート9002に紐付け
    udp_sock .bind((server_address, udp_server_port))

    # clients: クライアントアドレス -> {'last_seen': datetime, 'fail_count': int}
    clients = {}  

    # クライアントのタイムアウト時間（秒）
    TIMEOUT_SECONDS = 60  # 1分

    # 連続送信失敗で削除する閾値
    MAX_FAIL_COUNT = 3

    while True:
        print('\nwaiting to receive message')
        
        #データ受信
        try:
            data, address = udp_sock .recvfrom(4096)
        except Exception as e:
            print("Error receiving data:", e)
            continue
            
        now = datetime.now()
        
        #クライアントリストに追加・更新
        if address not in clients:
                print(f"New client connected: {address}")
                clients[address] = {'last_seen': now, 'fail_count': 0}
        else:
                clients[address]['last_seen'] = now
                clients[address]['fail_count'] = 0  # メッセージ来てるので失敗カウントリセット
                
        usernamelen = data[0]
        username = data[1:1+usernamelen].decode('utf-8') #ユーザー名を復元
        message = data[1+usernamelen:].decode('utf-8') #メッセージ本文を復元
        print(f"From {username}@{address}: {message}")

        # 古いクライアントのクリーンアップ
        to_remove = []
        for client_addr, info in clients.items():
                if now - info['last_seen'] > timedelta(seconds=TIMEOUT_SECONDS):
                    print(f"Removing inactive client: {client_addr}")
                    to_remove.append(client_addr)
        for client_addr in to_remove:
                del clients[client_addr]

        if data:
            # 他のすべてのクライアントにリレー送信（送信元は除く）
            for client_addr in list(clients.keys()):
                if client_addr == address:
                    continue
                try:
                    udp_sock .sendto(data, client_addr)
                    print(f"Relayed to {client_addr}")
                except Exception as e:
                    print(f"Failed to send to {client_addr}: {e}")
                    clients[client_addr]['fail_count'] += 1
                    if clients[client_addr]['fail_count'] >= MAX_FAIL_COUNT:
                        print(f"Removing client due to repeated send failures: {client_addr}")
                        del clients[client_addr]

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    udp_thread = threading.Thread(target=udp_server, daemon=True)

    tcp_thread.start()
    udp_thread.start()

    tcp_thread.join()
    udp_thread.join() 