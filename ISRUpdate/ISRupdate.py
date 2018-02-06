from netmiko import ConnectHandler
from paramiko.ssh_exception import SSHException 
from concurrent.futures import ThreadPoolExecutor
import sys
import re


NewIOSImage = "c2900-universalk9-mz.SPA.156-3.M3a.bin";
NewIOSImageMD5 = "357bbcd419fc068c3833628274f2f1a1";
FtpPatch = "ftp://10.27.1.117/";
            
USER = "user";
PASSWORD = "pass";
ENABLE_PASS = PASSWORD;



###################################

def UpdateIOS(ssh, IP):
    print(IP + ': copy '+FtpPatch+NewIOSImage+' flash:'); 
    result=ssh.send_command('copy '+FtpPatch+NewIOSImage+' flash: \n\r\n\r\n\r', max_loops=1000, delay_factor=20);
    if re.search('Error', result):
        print(IP + ": FTP Error");
        return("Error connect to FTP");
    else:
        #Veryfy
        print(IP + ': verify '+NewIOSImage);
        CorrectIOS=False;
        VerifyMD5=ssh.send_command(str('verify '+NewIOSImage), delay_factor=5).split('\n');
        for line in VerifyMD5:
            match = re.search(NewIOSImageMD5.upper(), line);
            if match: CorrectIOS=True;
            
        if CorrectIOS: 
            print(IP + ": MD5 Match");
            bootstr = ssh.send_command("show running-config | include boot system").split('\n'); 
            
            print(IP + ': boot system flash flash0:'+NewIOSImage);
            ssh.send_config_set('boot system flash flash0:'+NewIOSImage);        
            for line in bootstr: 
                ssh.send_config_set("no "+line);
                print(IP + ": no "+line);
            print(IP + ": Write and reload at 1:00");
            ssh.send_command("wr\n\r\n\r");
            ssh.send_command("reload at 1:00\n\r\n\r\n\r");
            return("Update success");
        else:
            print(IP + ": MD5 NotMatch");
            print(IP + ': delete '+NewIOSImage);
            ssh.send_command('delete '+NewIOSImage+'\n\r\n\r\n\r');
            return("Error copy from FTP (MD5 error)");

###############################   
        

def connect(IP):
    i=0;
    iosver={};
    NewestIOS=False;
    iosver={};

    print ( IP + ": Connection to device" );
    DEVICE_PARAMS = {'device_type': 'cisco_ios',
                     'ip': IP,
                     'username':USER,
                     'password':PASSWORD,
                     'secret':ENABLE_PASS }
    try:
        ssh = ConnectHandler(**DEVICE_PARAMS);
        ssh.enable();
    except (EOFError, SSHException):
        print( IP + ": SSH is not connect for user "+ USER);
        
        DEVICE_PARAMS = {'device_type': 'cisco_ios',                ### Try with another user
                     'ip': IP,
                     'username':'admin',
                     'password':PASSWORD,
                     'secret':ENABLE_PASS }
        try:
            ssh = ConnectHandler(**DEVICE_PARAMS);
            ssh.enable();
        except (EOFError, SSHException):
            print( IP + ": SSH is not enabled for this device.");
            return(IP+": Can`t connect");
    
    
    
    result = ssh.send_command("dir").split('\n');

    for line in result:
        match = re.search('c2900-universal\S+.SPA.(\d{3})-(\d).M(\d)\D*.bin', line);
        if match:
            iosver.update({ i : {'bin' : match.group(0) ,'ios': match.group(1),'ver': match.group(2), 'M': match.group(3)}});
            if match.group(0)==NewIOSImage:  NewestIOS=True;
            print(IP + ': ', i, iosver[i]['bin']); 
            i=i+1;            
    CountIOS=i;

         
    if NewestIOS==False:
        if CountIOS==1:
            print (IP + ": One Image! Loading new image...");
            UpdateResult=UpdateIOS(ssh, IP);
               
        elif CountIOS==2:
            print (IP + ': Two Images! Delete oldest and loading new image...');
            MinIOSver=0;
            for i in range(CountIOS-1):
                if (int(iosver[i+1]['ios']+iosver[i+1]['ver']+iosver[i+1]['M']) < int(iosver[i]['ios']+iosver[i]['ver']+iosver[i]['M'])): MinIOSver = i+1;
            print(IP + ': delete '+iosver[MinIOSver]['bin']);
            ssh.send_command('delete '+iosver[MinIOSver]['bin']+'\n\r\n\r\n\r');
            UpdateResult=UpdateIOS(ssh, IP);
            
        else: 
            print (IP + ': Something wrong!');
            UpdateResult="Unexpected error";
    else: 
        print(IP + ': Already updated');
        UpdateResult="Already updated";

    ssh.disconnect();
    iosver.clear();
    print (IP + ": Disconnect device");
    return(IP+": "+UpdateResult);
    
    
###################################
#             MAIN
###################################   

if __name__ == '__main__':
    devices=[];
    devcount=0;
    
    f = open('UPDATE.txt');
    DEVICES_IP = f.read().rstrip().split('\n'); 
    f.close();
    
    for IP in DEVICES_IP:
        devices.append(IP);
        devcount=devcount+1;
  
    with ThreadPoolExecutor(devcount) as executor:
        all_done=executor.map(connect, devices);
        State=list(all_done);
        print ('--------------------------------------\n               Job done!\n--------------------------------------');
        for RESULT in State:
            print (RESULT);
    
