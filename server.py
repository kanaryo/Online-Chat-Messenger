import socket

# AF_INETを使用し、UDPソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ブロードキャスト許可
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

server_address = '0.0.0.0'
#ポート9001で待ち受ける。
server_port = 9001
print('starting up on port {}'.format(server_port))

# ソケットを特殊なアドレス0.0.0.0とポート9001に紐付け
sock.bind((server_address, server_port))

clients = {}  # 接続中のクライアントを保持（アドレス: True）

while True:
   print('\nwaiting to receive message')
   
   #データ受信
   data, address = sock.recvfrom(4096)
   
   #クライアントリストに送信元アドレスを追加
   if address not in clients:
        clients[address] = True
        print(f"New client connected: {address}")
        
   usernamelen = data[0]
   username = data[1:1+usernamelen].decode('utf-8') #ユーザー名を復元
   message = data[1+usernamelen:].decode('utf-8') #メッセージ本文を復元
   print(f"From {username}@{address}: {message}")

   if data:
    #    sent = sock.sendto(data, ('255.255.255.255', 9050))
    # 他のすべてのクライアントにリレー送信（送信元は除く）
    for client_addr in clients:
        if client_addr != address:
            sock.sendto(data, client_addr)
            print(f"Relayed to {client_addr}")
