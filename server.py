import socket
import time
from datetime import datetime, timedelta

# AF_INETを使用し、UDPソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = '0.0.0.0'
#ポート9001で待ち受ける。
server_port = 9001
print('starting up on port {}'.format(server_port))

# ソケットを特殊なアドレス0.0.0.0とポート9001に紐付け
sock.bind((server_address, server_port))

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
       data, address = sock.recvfrom(4096)
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
            sock.sendto(data, client_addr)
            print(f"Relayed to {client_addr}")
        except Exception as e:
            print(f"Failed to send to {client_addr}: {e}")
            clients[client_addr]['fail_count'] += 1
            if clients[client_addr]['fail_count'] >= MAX_FAIL_COUNT:
                print(f"Removing client due to repeated send failures: {client_addr}")
                del clients[client_addr]