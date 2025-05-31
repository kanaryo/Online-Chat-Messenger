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

while True:
   print('\nwaiting to receive message')
   data, address = sock.recvfrom(4096)
   usernamelen = data[0]
   username = data[1:1+usernamelen].decode('utf-8') #ユーザー名を復元
   message = data[1+usernamelen:].decode('utf-8') #メッセージ本文を復元

#    print('received {} bytes from {}'.format(len(data), address))
#    print(data)

   print(f"From {username}@{address}: {message}")


   if data:
       sent = sock.sendto(data, ('255.255.255.255', 9050))
       print('sent {} bytes back to {}'.format(sent, address))
