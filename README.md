
Chat cu camere virtuale:
Server-ul are o lista de camere virtuale, fiercare camera avand asociata o adresa de multicast, si raspunde la pachetele primite pe un anumit port prin care livreaza lista camerelor virtuale cu adresele de multicast aferente;
In aplicatia server se pot adauga sau sterge camere virtuale;
La pornire, clientul trimite un pachet pe adresa de broascast a subretelei pe portul pe care asculta server-ul pentru a primi lista de camere virtuale si porturile lor aferente;
Clientul se poate adauga in grupul unei camere virtuale sau poate iesi din camera virtuala curenta, fiind la un moment dat in cel mult un grup al unei camere virtuale;
Clientul poate trimite mesaje text catre adresa de multicast aferenta camerei virtuale curente pe portul predefinit pentru comunicarea prin schimbul de mesaje;
Fiecare client asculta adresa de multicast a camerei virtuale in care se afla pe portul predefinit pentru mesaje, afisand mesajele primite;
La stergerea unei camere virtuale de catre server, precum si la adaugarea unei noi camere, server-ul va trimite un mesaj pe adresa de broadcast a subretelei si portul predefinit pentru comunicare.
