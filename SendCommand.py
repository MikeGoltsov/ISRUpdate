from netmiko import ConnectHandler
from paramiko.ssh_exception import SSHException 
from concurrent.futures import ThreadPoolExecutor
import sys
import re
import json
import requests




DEVICE_ROLE = 9   # 9-Core router, 11-Distribution router, 12-BPAS Router  1-Access Switch
DEVICE_TYPE = 3   # 1-1921, 2-2901, 3-2911, 10-SM-ES3G-16-P
DEVICE_REGION = '' # 79-nr


Token = '38b8916d335ce21fcf2c4cd0a0b0b9a35a23f619'
USER = "user"
PASSWORD = "pass"


def GetFromNetbox(Part):
    header = {'Content-Type': 'application/json', 'Accept' : 'application/json'}
    r = requests.get('http://netbox.local/api/'+Part+'/?format=json&limit=10000', headers=header)
    return r.json()

# def UpdateInNetbox(Part,Data):
#     header = {'Authorization': 'Token '+Token, 'Content-Type': 'application/json', 'Accept' : 'application/json'}
#     r = requests.patch('http://10.27.5.151:8080/api/'+Part+'/?format=json&limit=10000', headers=header, data=json.dumps(Data))
#     return r.json()

# def AddToNetbox(Part,Data):
#     header = {'Authorization': 'Token '+Token, 'Content-Type': 'application/json', 'Accept' : 'application/json'}
#     r = requests.post('http://10.27.5.151:8080/api/'+Part+'/?format=json', headers=header, data=json.dumps(Data))
#     return r.json()


def Connect(Input):
    print ( Input['ip'] + ": Connection to device" )
    DEVICE_PARAMS = {'device_type': 'cisco_ios',
                     'ip': Input['ip'],
                     'username':USER,
                     'password':PASSWORD,
                     'secret':PASSWORD }
    try:
        ssh = ConnectHandler(**DEVICE_PARAMS)
        ssh.enable()
    except:
        print( Input['ip'] + ": SSH is not connect for user "+ USER)
        
        DEVICE_PARAMS = {'device_type': 'cisco_ios',                ### Try with another user
                     'ip': Input['ip'],
                     'username':'admin',
                     'password':PASSWORD,
                     'secret':PASSWORD }
        try:
            ssh = ConnectHandler(**DEVICE_PARAMS)
            ssh.enable()
        except:
            print( Input['ip'] + ": SSH is not enabled for this device.")
            return(Input['ip']+": Can`t connect")
                
    
    # result = ssh.send_command("sh inv", delay_factor=5)#.split('\n')
    # if re.search("SM-ES3G",ssh.send_command("sh inv", delay_factor=5)):
    #     if re.search("15\.0\(2\)SE11",ssh.send_command("sh ver", delay_factor=5)):
    #         return (Input['ip']+': Ulready updated')
    #     else:
    #         ssh.send_command("archive download-sw ftp://10.27.1.117/c3560e-universalk9-tar.150-2.SE11.tar\n\r\n\r\n\r", max_loops=10000, delay_factor=100)
    #         ssh.send_command("wr\n\r\n\r", delay_factor=5)
    #         ssh.send_command("reload at 6:00\n\r\n\r\n\r", delay_factor=5)
    # else:
    #     return (Input['ip']+': Device mismatch')
    
    # if not re.search("15\.0\(2\)SE11",ssh.send_command("sh ver", delay_factor=5)):
    #     ssh.send_command("reload at 6:00\n\r\n\r\n\r", delay_factor=5)
    #     return (Input['ip']+': Another version')


    print(ssh.send_command("copy ftp://10.27.1.117/pp-adv-isrg2-157-3.M-23-32.2.0.pack flash:\n\r\n\r\n\r"))
    print(ssh.send_config_set("ip nbar protocol-pack flash:pp-adv-isrg2-157-3.M-23-32.2.0.pack force"))
    #ssh.send_config_set("no vstack")
    print(ssh.send_config_set("ip nbar custom kontinent_ndmp udp 10000"))

    ssh.send_command("wr\n\r\n\r\n\r")
    

    ssh.disconnect()
    return (Input['ip']+': Done')





    
###################################
#             MAIN
###################################   

if __name__ == '__main__':
    devicelist=[]

    Devices = GetFromNetbox('dcim/devices')
    Addresses = GetFromNetbox('ipam/ip-addresses')



    for no in range(Devices['count']): 
        if Devices['results'][no]['primary_ip'] and Devices['results'][no]['device_role']['id'] == DEVICE_ROLE and Devices['results'][no]['device_type']['id'] == DEVICE_TYPE and re.search('^'+DEVICE_REGION, Devices['results'][no]['name']): 
            IP = re.search('(\S+)/\d{1,2}', Devices['results'][no]['primary_ip']['address']).group(1).strip(' ')
            # print (IP)
            # print (Devices['results'][no]['name'])
            devicelist.append({'ip':IP, 'DeviceId':Devices['results'][no]['device_role']['id']})

    
    with ThreadPoolExecutor(len(devicelist)) as executor:
        all_done=executor.map(Connect, devicelist)
        State=list(all_done)
        print ('--------------------------------------\n               Job done!\n--------------------------------------')
        for RESULT in State:
            print (RESULT)


    # for no in range(Addresses['count']):
    #     print (Addresses['results'][no]['address'])
    #     if 'description' in Addresses['results'][no]:
    #         print (Addresses['results'][no]['description'])
    #         print (no)
    # print (Addresses['count'])