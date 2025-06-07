import socket
import os
from pathlib import Path
import uuid

def generate_token():
    return uuid.uuid4().hex.encode('utf-8')[:255]  # 最大255バイト

#IPv4,TCPを指定してソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#任意のIPアドレスからの接続を受け入れる
server_address = '0.0.0.0'
server_port = 9001

#ソケットをサーバのアドレスとポートに紐付けします。
sock.bind((server_address, server_port))

# サーバは一度に最大1つの接続を受け入れる
sock.listen(1)

rooms = {}  # ルーム名 → トークンマップ

while True:
    connection, client_address = sock.accept()
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
        
        
        