import socket
import threading
import json
import time
from datetime import datetime

from config import SERVER_PORT_DISCOVERY, CLIENT_BROADCAST_IP, MESSAGE_PORT, SERVER_NOTIFICATION_PORT

class ChatServer:
    def __init__(self):
        self.rooms = {}  
        self.next_multicast_ip_octet = 1 

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.bind(('', SERVER_PORT_DISCOVERY)) # Asculta pe toate interfetele

        self.notification_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.notification_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.notification_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Permite broadcast

        print(f"Serverul a pornit pe portul de descoperire: {SERVER_PORT_DISCOVERY}")
        print(f"Serverul va trimite notificari pe portul: {SERVER_NOTIFICATION_PORT}")


    def _generate_multicast_address(self):
        "Genereaza o adresa de multicast unica pentru o noua camera."
        # Clasele de adrese multicast sunt de la 224.0.0.0 la 239.255.255.255
       
        if self.next_multicast_ip_octet > 254:
            raise ValueError("Nu mai sunt adrese multicast disponibile (simplificat).")
        multicast_ip = f"239.0.0.{self.next_multicast_ip_octet}"
        self.next_multicast_ip_octet += 1
        return multicast_ip

    def add_room(self, room_name):
        if room_name in self.rooms:
            print(f"Camera '{room_name}' exista deja.")
            return

        try:
            multicast_ip = self._generate_multicast_address()
            self.rooms[room_name] = multicast_ip
            print(f"Camera '{room_name}' adaugata cu adresa multicast: {multicast_ip}")
            self.send_room_update_notification("add", room_name, multicast_ip)
        except ValueError as e:
            print(f"Eroare la adaugarea camerei: {e}")

    def delete_room(self, room_name):
        if room_name not in self.rooms:
            print(f"Camera '{room_name}' nu exista.")
            return

        multicast_ip = self.rooms.pop(room_name)
        print(f"Camera '{room_name}' stearsa (adresa multicast: {multicast_ip}).")
        self.send_room_update_notification("delete", room_name, multicast_ip)

    def get_room_list(self):
        "Returneaza lista camerelor virtuale cu adresele de multicast."
        return {
            "rooms": self.rooms,
            "message_port": MESSAGE_PORT # Clientul are nevoie si de portul de mesaje
        }

    def handle_discovery_requests(self):
        "Asculta cereri de descoperire (broadcast) de la clienti."
        while True:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                print(f"Cerere de descoperire primita de la {addr}: {data.decode()}")
                room_list_json = json.dumps(self.get_room_list())
                self.discovery_socket.sendto(room_list_json.encode(), addr)
                print(f"Lista camerelor trimisa catre {addr}")
            except Exception as e:
                print(f"Eroare in thread-ul de descoperire: {e}")

    def send_room_update_notification(self, action, room_name, multicast_ip):
        "Trimite o notificare broadcast la adaugarea/stergerea unei camere."
        notification = {
            "action": action, # "add" sau "delete"
            "room_name": room_name,
            "multicast_ip": multicast_ip,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            self.notification_socket.sendto(json.dumps(notification).encode(), (CLIENT_BROADCAST_IP, SERVER_NOTIFICATION_PORT))
            print(f"Notificare broadcast trimisa: {notification}")
        except Exception as e:
            print(f"Eroare la trimiterea notificarii broadcast: {e}")


    def run(self):
        # Porneste un thread separat pentru a gestiona cererile de descoperire
        discovery_thread = threading.Thread(target=self.handle_discovery_requests)
        discovery_thread.daemon = True # Thread-ul se va opri cand se opreste programul principal
        discovery_thread.start()

        # Interfata de administrare a serverului (consola)
        while True:
            command = input("Comanda (add <nume_camera> | del <nume_camera> | list | exit): ").strip().lower()
            if command.startswith("add "):
                room_name = command[4:].strip()
                if room_name:
                    self.add_room(room_name)
                else:
                    print("Numele camerei nu poate fi gol.")
            elif command.startswith("del "):
                room_name = command[4:].strip()
                if room_name:
                    self.delete_room(room_name)
                else:
                    print("Numele camerei nu poate fi gol.")
            elif command == "list":
                print("\n--- Camere virtuale ---")
                if self.rooms:
                    for name, ip in self.rooms.items():
                        print(f"  - {name}: {ip}")
                else:
                    print("Nu exista camere virtuale.")
                print("-----------------------\n")
            elif command == "exit":
                print("Opresc serverul...")
                break
            else:
                print("Comanda invalida.")

if __name__ == "__main__":
    server = ChatServer()
    server.run()