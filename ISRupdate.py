#!/usr/bin/python3
from netmiko import ConnectHandler
from paramiko.ssh_exception import SSHException 
from concurrent.futures import ThreadPoolExecutor
import sys
import re
import json
import requests
#import pycurl



NewIOSImage = "c2900-universalk9-mz.SPA.157-3.M4.bin"
NewIOSImageMD5 = "0f65543e965cf417081171e6453360ec"

#NewIOSImage = "c1900-universalk9-mz.SPA.157-3.M3.bin"   # boot usbflash0:
#NewIOSImageMD5 = "c30f725a7a43f8a60fa1bcec73bd4ffc"
            
DEVICE_ROLE = 9  # 9-Core router, 11-Distribution router, 12-BPAS Router 
DEVICE_TYPE = 3   # 1-1921, 2-2901, 3-2911
DEVICE_REGION = '41-' # 79-nr

USER = "user"
PASSWORD = "pass"
ENABLE_PASS = PASSWORD
FtpPatch = "ftp://10.27.1.117/"
Token = '38b8916d335ce21fcf2c4cd0a0b0b9a35a23f619'


NewIOSImageType = re.search('(c\d900-universal)', NewIOSImage).group()  ## Define New IOS Image type



def GetFromNetbox(Part):
    header = {'Content-Type': 'application/json', 'Accept' : 'application/json'}
    r = requests.get('http://netbox.local/api/'+Part+'/?format=json&limit=10000', headers=header)
    return r.json()

###################################

def UpdateIOS(ssh, IP):
    print(IP + ': copy '+FtpPatch+NewIOSImage+' flash:')
    result=ssh.send_command('copy '+FtpPatch+NewIOSImage+' flash: \n\r\n\r\n\r', max_loops=10000, delay_factor=100)
    if re.search('Error', result):
        print(IP + ": FTP Error")
        return("Error connect to FTP")
    else:
        #Veryfy
        print(IP + ': verify '+NewIOSImage)
        CorrectIOS=False
        VerifyMD5=ssh.send_command(str('verify '+NewIOSImage), delay_factor=5).split('\n')
        for line in VerifyMD5:
            match = re.search(NewIOSImageMD5.upper(), line)
            if match: CorrectIOS=True
            
        if CorrectIOS: 
            print(IP + ": MD5 Match")
            bootstr = ssh.send_command("show running-config | include boot system", delay_factor=5).split('\n')
            
            print(IP + ': boot system flash flash0:'+NewIOSImage)
            ssh.send_config_set('boot system flash flash0:'+NewIOSImage, delay_factor=5)
            for line in bootstr: 
                ssh.send_config_set("no "+line)
                print(IP + ": no "+line)
            print(IP + ": Write and reload at 3:45")
            ssh.send_command("wr\n\r\n\r", delay_factor=5)
            ssh.send_command("reload at 3:45\n\r\n\r\n\r", delay_factor=5)
            return("Update success")
        else:
            print(IP + ": MD5 NotMatch")
            print(IP + ': delete '+NewIOSImage)
            ssh.send_command('delete '+NewIOSImage+'\n\r\n\r\n\r', delay_factor=5)
            return("Error copy from FTP (MD5 error)")

###############################   
        

def connect(IP):
    i=0
    iosver={}
    NewestIOS=False
    
    print ( IP + ": Connection to device" )
    DEVICE_PARAMS = {'device_type': 'cisco_ios',
                     'ip': IP,
                     'username':USER,
                     'password':PASSWORD,
                     'secret':ENABLE_PASS }
    try:
        ssh = ConnectHandler(**DEVICE_PARAMS)
        ssh.enable()
    except (EOFError, SSHException):
        print( IP + ": SSH is not connect for user "+ USER)
        
        DEVICE_PARAMS = {'device_type': 'cisco_ios',                ### Try with another user
                     'ip': IP,
                     'username':'admin',
                     'password':PASSWORD,
                     'secret':ENABLE_PASS }
        try:
            ssh = ConnectHandler(**DEVICE_PARAMS)
            ssh.enable()
        except (EOFError, SSHException):
            print( IP + ": SSH is not enabled for this device.")
            return(IP+": Can`t connect")
    
    
    # ssh.send_config_set("ip ftp source-interface Loopback 0", delay_factor=5)
    # ssh.send_command("wr\n\r\n\r", delay_factor=5)

    result = ssh.send_command("dir", delay_factor=5).split('\n')
    
    for line in result:
        match = re.search(NewIOSImageType+'\S+.SPA.(\d{3})-(\d).M(\d)\D*.bin', line)
        if match:
            iosver.update({ i : {'bin' : match.group(0) ,'ios': match.group(1),'ver': match.group(2), 'M': match.group(3)}})
            if match.group(0)==NewIOSImage:  NewestIOS=True
            print(IP + ': ', i, iosver[i]['bin'])
            i=i+1
    CountIOS=i

         
    if NewestIOS==False:
        if CountIOS==0:
            print (IP + ': No images! Maybe device type mismatch!')
            UpdateResult="No images! Maybe device type mismatch!"

        elif CountIOS==1:
            print (IP + ": One Image! Loading new image...")
            UpdateResult=UpdateIOS(ssh, IP)
               
        elif CountIOS==2:
            print (IP + ': Two Images! Delete old and loading new image...')
            MinIOSver=0
            for i in range(CountIOS-1):
                if (int(iosver[i+1]['ios']+iosver[i+1]['ver']+iosver[i+1]['M']) < int(iosver[i]['ios']+iosver[i]['ver']+iosver[i]['M'])): MinIOSver = i+1    # Oldest or newest
            print(IP + ': delete '+iosver[MinIOSver]['bin'])
            ssh.send_command('delete '+iosver[MinIOSver]['bin']+'\n\r\n\r\n\r', delay_factor=5)
            UpdateResult=UpdateIOS(ssh, IP)
            
        else: 
            print (IP + ': Something wrong!')
            UpdateResult="Unexpected error"
    else: 
        print(IP + ': Already updated')
        UpdateResult="Already updated"

    ssh.disconnect()
    iosver.clear()
    print (IP + ": Disconnect device")
    return(IP+": "+UpdateResult)
    
    
###################################
#             MAIN
###################################   

if __name__ == '__main__':
    devicelist=[]
    
    Devices = GetFromNetbox('dcim/devices')
    
    for no in range(Devices['count']): 
        if Devices['results'][no]['primary_ip'] and not re.search('FSTEK', Devices['results'][no]['name'], re.IGNORECASE) and Devices['results'][no]['device_role']['id'] == DEVICE_ROLE and re.search('^'+DEVICE_REGION, Devices['results'][no]['name']): 
            IP = re.search('(\S+)/\d{1,2}', Devices['results'][no]['primary_ip']['address']).group(1).strip(' ')
            devicelist.append(IP)
  
    
    with ThreadPoolExecutor(len(devicelist)) as executor:
        all_done=executor.map(connect, devicelist)
        State=list(all_done)
        print ('--------------------------------------\n               Job done!\n--------------------------------------')
        for RESULT in State:
            print (RESULT)
    