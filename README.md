1 2 3

# Implementare

## **1. Tabela de comutare**
  Am creeat o tabela de comutare in care si, de fiecare data cand am primit un cadru pe un switch, am adaugat adresa sursa in tabela.
  Apoi am verificat daca adresa destinatie este unicast sau multicast. In caz ca este unicast am verificat daca am deja destinatia mapata la o interfata. Daca da trimit direct mesajul, daca nu fac broadcast.
  Daca adresa este multicast fac direct broadcast.

## **2. VLAN**
  Inainte de a incepe implementarea pentru **VLAN** a fost nevoie sa citesc configurarile interfetelor pentru a afla in ce **VLAN** se afla fiecare *Host*.
  Pentru a implementa **VLAN**-urile am avut de verificat urmatoarele cazuri la trimiterea unui cadru:
  - *Switch*->*Switch*: Interfata pe care a venit este a unui *Switch* si trebuie sa se duca la un alt switch.
  Pentru acest caz doar trimit datele asa cum le-am primit deoarece este deja tagged cu id-ul **VLAN**-ului pe care a venit.
  - *Switch*->*Host*: Pentru a trimite de la un *Switch* la un host a fost nevoie sa scot id-ul **VLAN**-ului. 
  De asemenea a trebuit verificat daca **VLAN**-ul pe care merg este acelasi cu **VLAN**-ul pe care il trimit.
  - *Host*->*Switch*: Pentru a trimite un cadru de la un *Host* la un *Switch* a trebuit sa adaug id-ul **VLAN**-ului din care face parte acest *Host*.
  - *Host*->*Host*: Interfata pe care a venit este un *Host* iar interfata pe care pleaca este tot un *Host*, deci trebuie verificat daca aceste *Host*-uri fac parte din acelasi **VLAN**.

## **3. STP**
  In implementarea pe care am facut-o, porturile unui switch pot avea urmatoarele valori:
  - 0 = ***Empty(Nu este inca atribuit un tip de port)***
  - 1 = ***Designated***
  - 2 = ***Root Port***
  - -1 = ***Blocked***

  Fiecare switch trimite un pachet de tip **BDPU** la intervale de o secunda. Pachetul are urmatorul continut:
  ```
  mac_bdpu | mac_sursa | root_bridge_id | sender_path_cost | sender_bridge_id
  ```
  Cand switchul primeste un pachet de tip **BPDU**(mac-ul **BPDU** este mereu 01:80:C2:00:00:00) va verifica urmatoarele cazuri:
  - *ID*-ul primit este mai mic decat al *Switch*-ului curent: Se considera ca interfata pe care a venit este ***Root*** deci se va marca ca root si se va adauga 10 la valoarea costului.
  Apoi se verifica daca *Switch*-ul credea ca el este **Root Bridge**(initial toate rooter-ele cred ca sunt **Root Bridge**). 
  Daca da toate interfetele catre alte *Switch*-uri se trec pe ***Blocked***. Apoi trimit tuturor *Switch*-urilor cu porturile ***Designated*** un update. 
  - Pachet **BPDU** venit de la **Root Bridge**: Updatez costul si verific ca interfata pe care a venit sa nu fie ***Blocked***
  - Pachet venit de la un alt *Switch* care nu e **Root bridge**: Setez portul pe ***Blocked***
  - Daca nu este unul din cazurile de mai sus aruc Pachetul
  - Se verifica daca *Switch*-ul curent este **Root Bridge** si daca da se seteaza toate porturile ***Designated***
  

## Running

```bash
sudo python3 checker/topo.py
```

This will open 9 terminals, 6 hosts and 3 for the switches. On the switch terminal you will run 

```bash
make run_switch SWITCH_ID=X # X is 0,1 or 2
```

The hosts have the following IP addresses.
```
host0 192.168.1.1
host1 192.168.1.2
host2 192.168.1.3
host3 192.168.1.4
host4 192.168.1.5
host5 192.168.1.6
```

We will be testing using the ICMP. For example, from host0 we will run:

```
ping 192.168.1.2
```

Note: We will use wireshark for debugging. From any terminal you can run `wireshark&`.
