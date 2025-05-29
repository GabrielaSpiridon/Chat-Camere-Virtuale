import socket
import threading
import json
import time
import struct # Pentru a lucra cu adresele de multicast

from config import SERVER_PORT_DISCOVERY, CLIENT_BROADCAST_IP, MESSAGE_PORT, SERVER_NOTIFICATION_PORT

class ChatClient:
    def __init__(self):
        self.rooms = {}
        self.current_room = None
        self.multicast_group_socket = None # Socket pentru a asculta mesaje in camera curenta

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Permite broadcast

        self.notification_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.notification_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.notification_socket.bind(('', SERVER_NOTIFICATION_PORT)) # Asculta notificari de la server

        print(f"Clientul a pornit.")
        print(f"Clientul va asculta notificari de la server pe portul: {SERVER_NOTIFICATION_PORT}")

    def discover_server(self):
        """Trimite un pachet broadcast pentru a descoperi serverul si a primi lista de camere."""
        print(f"Caut serverul pe {CLIENT_BROADCAST_IP}:{SERVER_PORT_DISCOVERY}...")
        try:
            self.discovery_socket.sendto(b"DISCOVER_SERVER", (CLIENT_BROADCAST_IP, SERVER_PORT_DISCOVERY))
            self.discovery_socket.settimeout(5) # Asteapta un raspuns timp de 5 secunde
            data, server_address = self.discovery_socket.recvfrom(4096)
            self.discovery_socket.settimeout(None) # Reseteaza timeout-ul
            room_info = json.loads(data.decode())
            self.rooms = room_info["rooms"]
            print(f"Lista camerelor primita de la {server_address}:")
            self.display_rooms()
            return True
        except socket.timeout:
            print("Serverul nu a raspuns in timp util. Asigura-te ca serverul ruleaza.")
            return False
        except Exception as e:
            print(f"Eroare la descoperirea serverului: {e}")
            return False

    def display_rooms(self):
        """Afiseaza camerele disponibile."""
        if self.rooms:
            print("\n--- Camere disponibile ---")
            for name, ip in self.rooms.items():
                print(f"  - {name} (Adresa Multicast: {ip})")
            print("--------------------------\n")
        else:
            print("Nu exista camere disponibile momentan.")

    def join_room(self, room_name):
        """Clientul se alatura unui grup multicast al unei camere virtuale."""
        if room_name not in self.rooms:
            print(f"Camera '{room_name}' nu exista.")
            return

        if self.current_room:
            print(f"Esti deja in camera '{self.current_room}'. Paraseste mai intai camera curenta.")
            return

        multicast_ip = self.rooms[room_name]
        print(f"Incerc sa ma alatur camerei '{room_name}' (Adresa Multicast: {multicast_ip})...")

        try:
            # Creare socket UDP pentru multicast
            self.multicast_group_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.multicast_group_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

   
            self.multicast_group_socket.bind(('', MESSAGE_PORT))

           
            mreq = struct.pack("4sl", socket.inet_aton(multicast_ip), socket.INADDR_ANY)
            self.multicast_group_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            self.current_room = room_name
            print(f"Te-ai alaturat camerei '{self.current_room}'. Acum poti trimite mesaje.")

            # Porneste un thread pentru a asculta mesaje in camera
            message_listener_thread = threading.Thread(target=self.listen_for_multicast_messages)
            message_listener_thread.daemon = True
            message_listener_thread.start()

        except Exception as e:
            print(f"Eroare la alaturarea in camera '{room_name}': {e}")
            if self.multicast_group_socket:
                self.multicast_group_socket.close()
            self.multicast_group_socket = None

    def leave_room(self):
        """Clientul paraseste grupul multicast al camerei curente."""
        if not self.current_room:
            print("Nu esti in nicio camera.")
            return

        multicast_ip = self.rooms.get(self.current_room)
        if multicast_ip and self.multicast_group_socket:
            print(f"Parasind camera '{self.current_room}' (Adresa Multicast: {multicast_ip})...")
            try:
                # Paraseste grupul multicast
                mreq = struct.pack("4sl", socket.inet_aton(multicast_ip), socket.INADDR_ANY)
                self.multicast_group_socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                self.multicast_group_socket.close()
                self.multicast_group_socket = None
                print(f"Ai parasit camera '{self.current_room}'.")
            except Exception as e:
                print(f"Eroare la parasirea camerei: {e}")
        self.current_room = None

    def send_message(self, message):
        """Trimite un mesaj catre adresa de multicast a camerei curente."""
        if not self.current_room:
            print("Trebuie sa te alaturi unei camere pentru a trimite mesaje.")
            return

        multicast_ip = self.rooms[self.current_room]
        try:
            # Creare socket UDP pentru trimiterea mesajelor multicast
           
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2) # TTL = 2, pentru a nu iesi din retea

            full_message = f"[{socket.gethostname()}] {message}" # Adauga numele hostului
            send_socket.sendto(full_message.encode(), (multicast_ip, MESSAGE_PORT))
            send_socket.close()
            print(f"Mesaj trimis in camera '{self.current_room}': {full_message}")
        except Exception as e:
            print(f"Eroare la trimiterea mesajului: {e}")

    def listen_for_multicast_messages(self):
        """Asculta mesaje pe adresa de multicast a camerei curente."""
        if not self.multicast_group_socket:
            print("Nu ai un socket de multicast deschis pentru a asculta mesaje.")
            return

        print(f"Ascult mesaje in camera '{self.current_room}'...")
        while self.current_room and self.multicast_group_socket:
            try:
                data, addr = self.multicast_group_socket.recvfrom(1024)
                print(f"\n[MESAJ] De la {addr[0]}: {data.decode()}\n")
            except socket.timeout:
                pass #  doar verifica conditia de oprire
            except Exception as e:
                if self.current_room: # Daca s-a inchis socket-ul in timp ce era in camera, e o eroare
                    print(f"Eroare la primirea mesajelor multicast: {e}")
                break # Iesi din bucla daca socket-ul e inchis sau nu mai esti in camera

    def listen_for_server_notifications(self):
        """Asculta notificari broadcast de la server (adaugare/stergere camere)."""
        while True:
            try:
                data, addr = self.notification_socket.recvfrom(1024)
                notification = json.loads(data.decode())
                action = notification.get("action")
                room_name = notification.get("room_name")
                multicast_ip = notification.get("multicast_ip")
                timestamp = notification.get("timestamp")

                print(f"\n[NOTIFICARE SERVER] [{timestamp}] Camera '{room_name}' ({multicast_ip}) a fost {action}a.\n")

                # Actualizeaza lista de camere a clientului
                if action == "add":
                    self.rooms[room_name] = multicast_ip
                elif action == "delete":
                    if room_name in self.rooms:
                        del self.rooms[room_name]
                        # Daca camera stearsa e cea in care suntem, o parasim automat
                        if self.current_room == room_name:
                            print(f"Camera curenta '{room_name}' a fost stearsa. Parasesti automat camera.")
                            self.leave_room()
                self.display_rooms() # Reafiseaza camerele actualizate

            except Exception as e:
                print(f"Eroare in thread-ul de notificari server: {e}")


    def run(self):
        # Porneste un thread pentru a asculta notificari de la server
        notification_thread = threading.Thread(target=self.listen_for_server_notifications)
        notification_thread.daemon = True
        notification_thread.start()

    
        if not self.discover_server():
            print("Clientul nu a putut contacta serverul. Asigura-te ca serverul ruleaza.")

        while True:
            command = input("Comanda (join <nume_camera> | leave | send <mesaj> | rooms | refresh | exit): ").strip().lower()
            if command.startswith("join "):
                room_name = command[5:].strip()
                if room_name:
                    self.join_room(room_name)
                else:
                    print("Numele camerei nu poate fi gol.")
            elif command == "leave":
                self.leave_room()
            elif command.startswith("send "):
                message = command[5:].strip()
                if message:
                    self.send_message(message)
                else:
                    print("Mesajul nu poate fi gol.")
            elif command == "rooms":
                self.display_rooms()
            elif command == "refresh":
                self.discover_server() 
            elif command == "exit":
                print("Opresc clientul...")
                self.leave_room() 
                break
            else:
                print("Comanda invalida.")

if __name__ == "__main__":
    client = ChatClient()
    client.run()