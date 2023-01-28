import re
import ipaddress
from netmiko import ConnectHandler
from types import SimpleNamespace 


#Welcome Banner
print(" ")
print("Welcome to the routingloop.net OSPF Autoconfiguration Tool. This is a Python script to automate the configuation of OSPF routing on Cisco IOS routers.")
print(" ")
#Gather device name from user. The hostname will need to be in local hosts file until DNS is working.
deviceName = input("What device would you like to configure for OSPF? ")
print(" ")
#Gather OSPF process ID from user 
ospfProcessID = input("What is the OSPF process ID? ")
print(" ")
#Ask user if an OSPF RID should be specified with Y/N answer. If yes, logic later in the script will gather RID from user. 
ridYN = input("Would you like to specify an OSPF router ID? (Y/N) ")



# RegEx for identifying ipv4 dotted decimal 
IPpattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'




#Define Device Vars
net_connect = ConnectHandler(device_type='cisco_ios', host=deviceName, username='username', password='password', secret='password') 

net_connect.enable()
print(net_connect.find_prompt())

#Define command to see which interfaces are numbered 
showIpIntBriefCMD = "show ip interface brief | ex unass"

#Send show ip int brief to device
showIpIntBrief= net_connect.send_command(showIpIntBriefCMD, use_textfsm=True)

#Count total numbered interfaces. This is used for subtraction while iterating through IPv4 interfaces. 
intfCount = len(showIpIntBrief)


#Configure OSPF Router ID if desired.
if ridYN == "y" or ridYN == "Y" or ridYN == "yes" or ridYN == "Yes" or ridYN == "YES":
    routerID = input("Please enter the ospf router ID in 32 bit dotted decimal: ")
    print(" ")

    ospfRIDCMD = ["router ospf " + ospfProcessID,
    "router-id " + routerID ]

    ospfRIDSend= net_connect.send_config_set(ospfRIDCMD)

else:
    print("The default router ID selection process will be used.")
    print(" ")



intf = "interface"

while intfCount > 0:
    # Looping logic to iterate through interfaces with ipv4 addresses 
    intfCountStr = str(intfCount)
    intfCount = intfCount - 1
    intfID = intf + intfCountStr
    intfID = showIpIntBrief[0]
    showIpIntBrief.pop(0)
    intf = intfID.get("intf")
    
    #Get interface IP address and parse out address 
    showRunIntCMD = "show run interface" + " " + intf + " | inc address"
    showRunIntSend= net_connect.send_command(showRunIntCMD, use_textfsm=True)
    addr = " "
    mask = " "
    while addr == " " and mask == " ":
        addr = re.search(IPpattern, showRunIntSend).group()
        addrrm = re.sub(addr, " ", showRunIntSend)
        mask = re.search(IPpattern, addrrm).group()

    ipAndMask = addr + "/" + mask

    print("----------------------------------------------------------------")
    print("Moving on to network statement configuration.")
    print(" ")




    #Gather interface CDP Neighbor Details
    showCdpNeiCMD= "show cdp nei " + intf

    showCdpNei= net_connect.send_command(showCdpNeiCMD, use_textfsm=True)

    print("This is the CDP Neighbor output for " + intf + ": ")
    print(showCdpNei)

    
    # Accept interface IP and subnet mask 
    netID= ipaddress.IPv4Interface(ipAndMask)
    #Determine Network ID with CIDR Notation
    NetIDCidr = netID.network
    #Flip CIDR bits to wildcard mask 
    NetIDWild = NetIDCidr.with_hostmask
    #Convert format to ipaddress with CIDR for parsing 
    intfCidr = ipaddress.IPv4Network(NetIDWild)
    #Define var for interface Network ID 
    intfNetID = intfCidr.network_address
    #Define var for interface Wildcard mask 
    intfWild = intfCidr.hostmask
    print(" ")
    netID=str(netID)
    print(" ")
    print("The " + intf + " IP configuration is " + netID + ".")
    print(" ")
    ospfArea = input("What OSPF area should " + intf + " be in? ")
    print("----------------------------------------------------------------")
    print(" ")
    ospfArea = str(ospfArea)
    intfNetIDSTR = str(intfNetID)
    intfWildSTR = str(intfWild)
    ospfConfigCMD = ["router ospf " + ospfProcessID,
        "network " + intfNetIDSTR + " " + intfWildSTR + " " + "area" + " " + ospfArea ]

    ospfConfigSend= net_connect.send_config_set(ospfConfigCMD)


#Define command to see new ospf configuration 
showRunOspfCMD= "show running-config | sec ospf " + ospfProcessID

#Send "show run ospf | sec $proc ID"
showRunOspf= net_connect.send_command(showRunOspfCMD, use_textfsm=False)   
print(" ")
print("The following configuration has been applied:")
print(showRunOspf)


print(" ")
wrMemIn = input("Would you like to save the configuation? (Y/N) ")

if wrMemIn == "y" or wrMemIn == "Y" or wrMemIn == "yes" or wrMemIn == "Yes":
    copR_SCMD = "copy running-config startup-config"
    copRsSend = net_connect.send_command_timing(copR_SCMD)
    if 'Destination filename' in copRsSend:
        copRsSend += net_connect.send_command_timing('\n')
    print(copRsSend)


else:
    print("The configuration will not be saved.")