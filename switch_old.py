#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def create_bpdu(priority, src_mac, root_bridge_id, sender_path_cost, own_bridge_id):
    # return struct.pack('!H', 0x8200) + struct.pack('!H', src_mac) + struct.pack('!H', vlan_id & 0x0FFF) + struct.pack('!H', root_bridge_id) + struct.pack('!H', sender_path_cost) + struct.pack('!H', own_bridge_id)
    bpdu_mac = bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x00])
    # return bpdu_mac + src_mac +  + struct.pack('!H', root_bridge_id) + struct.pack('!H', sender_path_cost) + struct.pack('!H', own_bridge_id)
    # print("CREATE BPDU SENDER PATH COST: {}".format(sender_path_cost))
    return bpdu_mac + src_mac + struct.pack('!H', priority & 0x0FFF) + struct.pack('!H', root_bridge_id) + struct.pack('!H', sender_path_cost) + struct.pack('!H', own_bridge_id)

def send_bdpu_every_sec(stp, own_bridge_id, root_bridge_id, vlan_ids, priority, interfaces):
    while True:
        # TODO Send BDPU every second if necessary
        if stp[len(interfaces)]: # Root Bridge
            print("THREAD OBID: {}".format(own_bridge_id))
            print("THREAD RBID: {}".format(root_bridge_id))
            for i in interfaces:
                if vlan_ids[i] == -1: # Send on trunk
                    root_bridge_id = own_bridge_id
                    sender_path_cost = 0
                    sender_bridge_id = own_bridge_id
                    # print("ThreadFunc rbid: {}".format(root_bridge_id))
                    # print("ThreadFunc senderbid: {}".format(sender_bridge_id))
                    bpdu = create_bpdu(priority, get_switch_mac(), root_bridge_id, sender_path_cost, own_bridge_id)
                    send_to_link(i, bpdu, 20)

        time.sleep(1)

def isunicast(mac):
    return (mac[0] & 0x01) == 0

def readCfgFile(switch_id):
    file = open("./configs/switch"+str(switch_id)+".cfg", "r")
    lines = file.readline()
    priority = int(lines)
    print("CFG priority: {}".format(priority))
    interfaces = []
    for i in range(4):
        lines = file.readline()
        list = lines.split(" ")
        # print(list)
        if list[1].strip() == 'T':
            interfaces.append(-1)
        else:
            interfaces.append(int(list[1].strip()))
    print(interfaces)
    return priority, interfaces

def initSTP(interfaces, priority):
    stp = []
    for i in interfaces:
        if interfaces[i] == -1: # Block trunk
            # stp[i] = -1 # Blocked interface
            stp.append(-1)
        else: # Set other interfaces to nothing
            # stp[i] = 0 # Nothing
            stp.append(0)
    stp.append(1) # I am rootbridge
    print(type(stp))
    print("INTERFACES LEN: {}".format(len(interfaces)))
    print("INIT priority: {}".format(priority))
    root_bridge_id = priority
    own_bridge_id = priority
    root_path_cost = 0
    print("INIT root_bridge_id: {}".format(root_bridge_id))
    print("INIT own_bridge_id: {}".format(own_bridge_id))

    for i in interfaces:
        stp[i] = 1 # Designated
    
    return stp, own_bridge_id, root_bridge_id, root_path_cost
    

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    priority, vlan_ids = readCfgFile(switch_id)

    stp, own_bridge_id, root_bridge_id, root_path_cost = initSTP(vlan_ids, priority)
    print("INIT2 stp: {}".format(stp))
    print("INIT2 own_bridge_id: {}".format(own_bridge_id))
    print("INIT2 root_bridge_id: {}".format(root_bridge_id))
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec, args=(stp, own_bridge_id, root_bridge_id, vlan_ids, priority, interfaces))
    t.start()

    MAC_Table = {}

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        dest_mac_int = dest_mac
        src_mac_int = src_mac

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        # print(f'Destination MAC: {dest_mac}')
        # print(f'Source MAC: {src_mac}')
        # print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning
        MAC_Table[src_mac_int] = interface
        # BDPU mac = 01:80:C2:00:00:00
        if dest_mac_int == bytes([0x01, 0x80, 0xc2, 0x00, 0x00, 0x00]): # BPDU Package
#    return bpdu_mac + src_mac + create_vlan_tag(priority) + struct.pack('!H', root_bridge_id) + struct.pack('!H', sender_path_cost) + struct.pack('!H', own_bridge_id)
            print("BPDU")
            # p_dest_mac = data[0:6]
            # p_src_mac = data[6:12]
            # p_priority = int.from_bytes(data[12:14], byteorder='big')
            # p_rbid = int.from_bytes(data[14:16], byteorder='big')
            # p_sender_cost = int.from_bytes(data[16:18], byteorder='big')
            # p_own_bridge_id = int.from_bytes(data[18:20], byteorder='big')
            # print("p_dest_mac: {}".format(p_dest_mac))
            # print("p_src_mac: {}".format(p_src_mac))
            # print("p_priority: {}".format(p_priority))
            # print("p_rbid: {}".format(p_rbid))
            # print("p_sender_cost: {}".format(p_sender_cost))
            # print("p_own_bridge_id: {}".format(p_own_bridge_id))
            bpdu_rb_id = int.from_bytes(data[14:16], byteorder='big')
            # New Root Bridge
            if bpdu_rb_id < root_bridge_id:
                print("NEW RB")
                sender_path_cost = int.from_bytes(data[16:18], byteorder='big')
                root_path_cost = 10 + sender_path_cost
                stp[interface] = 2 # Root port
            
                # I was the Root Bridge
                if stp[len(interfaces)] == 1:
                    # own_bridge_id = bpdu_rb_id
                    stp[len(interfaces)] = 0 # No more Root Bridge
                    print("caca")
                    for i in interfaces:
                        if stp[i] != 2 and vlan_ids[i] == -1: # Not Root Port and Trunk
                            stp[i] = -1 # Blocked
                
                # Update the others
                sender_bridge_id = own_bridge_id
                sender_path_cost = root_path_cost
                bpdu = create_bpdu(priority, get_switch_mac(), root_bridge_id, sender_path_cost, sender_bridge_id)
                for i in interfaces:
                    if stp[i] == 1 and vlan_ids[i] == -1: # Designated trunk
                        send_to_link(i, bpdu, 20)
            
            elif bpdu_rb_id == root_bridge_id: # Same Root Bridge
                print("SAME RB")
                bpdu_sender_cost = int.from_bytes(data[16:18], byteorder='big')
                if stp[interface] == 2 and bpdu_sender_cost + 10 < root_path_cost:
                    root_path_cost = bpdu_sender_cost + 10
                elif stp[interface] != 2:
                    if bpdu_sender_cost > root_path_cost:
                        stp[interface] = 1
            
            elif int.from_bytes(data[14:16], byteorder='big') == own_bridge_id:
                print("OWN BRIDGE ID")
                stp[interface] = -1
            
            else:
                print("ELSE")
                continue
            
            if own_bridge_id == root_bridge_id:
                for i in interfaces:
                    stp[i] = 1 # Designated

        else:
            if isunicast(dest_mac_int): # unicast
                if dest_mac_int in MAC_Table: # knows where to go
                    if vlan_ids[interface] != -1: # Host
                        if vlan_ids[MAC_Table[dest_mac_int]] != -1: # Host->Host
                            if vlan_ids[MAC_Table[dest_mac_int]] == vlan_ids[interface]:
                                print("BAG Pl")
                                send_to_link(MAC_Table[dest_mac_int], data, length)
                        else: # Host->Switch
                            tagged_data = data[0:12] + create_vlan_tag(vlan_ids[interface]) + data[12:]
                            send_to_link(MAC_Table[dest_mac_int], tagged_data, length+4)
                    else: # Switch
                        if vlan_ids[MAC_Table[dest_mac_int]] == -1: # Switch->Switch
                            if stp[MAC_Table[dest_mac_int]] != -1:
                                send_to_link(MAC_Table[dest_mac_int], data, length)
                        else: # Switch->Host
                            if vlan_ids[MAC_Table[dest_mac_int]] == vlan_id:
                                untagged_data = data[0:12] + data[16:]
                                send_to_link(MAC_Table[dest_mac_int], untagged_data, length-4)
                else: # ARP
                    for i in interfaces:
                        if i != interface:
                            if vlan_ids[interface] != -1: # Host
                                if vlan_ids[i] != -1: # Host->Host
                                    if vlan_ids[i] == vlan_ids[interface]:
                                        send_to_link(i, data, length)
                                else: # Host->Switch
                                    tagged_data = data[0:12] + create_vlan_tag(vlan_ids[interface]) + data[12:]
                                    send_to_link(i, tagged_data, length+4)
                            else: # Switch
                                if vlan_ids[i] == -1: # Switch->Switch
                                    if stp[i] != -1:
                                        send_to_link(i, data, length)
                                else: # Switch->Host
                                    if vlan_ids[i] == vlan_id:
                                        untagged_data = data[0:12] + data[16:]
                                        send_to_link(i, untagged_data, length-4)
            else: # multicast
                for i in interfaces:
                    if i != interface:
                        if vlan_ids[interface] != -1: # Host
                            if vlan_ids[i] != -1: # Host->Host
                                if vlan_ids[i] == vlan_ids[interface]:
                                    send_to_link(i, data, length)
                            else: # Host->Switch
                                tagged_data = data[0:12] + create_vlan_tag(vlan_ids[interface]) + data[12:]
                                send_to_link(i, tagged_data, length+4)
                        else: # Switch
                            if vlan_ids[i] == -1: # Switch->Switch
                                if stp[i] != -1:
                                    send_to_link(i, data, length)
                            else: # Switch->Host
                                if vlan_ids[i] == vlan_id:
                                    untagged_data = data[0:12] + data[16:]
                                    send_to_link(i, untagged_data, length-4)

        for i in stp:
            print("stp: {}".format(i))

        # switch_mac = get_switch_mac()
        # switch_mac = ':'.join(f'{b:02x}' for b in switch_mac)
        # print("Switch MAC: {}".format(switch_mac))

        # print("CACAT")
        # print(sys.argv)

        # TODO: Implement VLAN support

        # TODO: Implement STP support

        # data is of type bytes.
        #send_to_link(i, data, length)

if __name__ == "__main__":
    main()
