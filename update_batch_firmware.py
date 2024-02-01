from netmiko import ConnectHandler
import threading
import argparse
import re
import time
import datetime

def update_batch(batch, skip_obmc_primary=False, skip_obmc_recovery=False):
    if batch == 0:
        ips = [
            'root@192.168.10.24',
            # 'root@192.168.10.23',
            # 'root@192.168.10.22',
            # 'root@192.168.10.21',
        ]
        ports = [3024]
        host_port = 3007
    else:
        ips = [
            'root@192.168.10.25',
            'root@192.168.10.26',
            'root@192.168.10.27',
            'root@192.168.10.28',
        ]
        ports = [3018, 3017, 3016, 3015]
        host_port = 3008

    start = datetime.datetime.now()
    print(f'Debug: Start: {start}')

    if(not skip_obmc_recovery):
        if(not skip_obmc_primary):

            print('************************************************\n OBMC Primary Partition\n************************************************')

            rm_ssh_hosts(host_port=host_port)

            for ip in ips:
                # Update Primary Partition
                send_files(['/root/sn20fw/obmc/obmc-3.4.1.mtd', '/root/sn20fw/obmc/obmc-3.4.1.mtd.md5'], '/dev/shm', ip, host_port=host_port)
                # send_file('/root/sn20fw/obmc/obmc-3.4.1.mtd.md5', '/dev/shm', ip, host_port=host_port)
                send_files(['/root/sn20fw/obmcupdate_1.4.sh'], '/usr/sbin/obmcupdate', ip, host_port=host_port)

            thread_xrdus(ports, 'obmcupdate -p primary -t bmc -f /dev/shm/obmc-3.4.1.mtd; date')

            thread_xrdus(ports, '/sbin/reboot -f')

        print('************************************************\n OBMC Recovery Partition\n************************************************')
        rm_ssh_hosts(host_port=host_port)

        for ip in ips:
            # Update Recovery Partition
            send_files(['/root/sn20fw/obmc/obmc-3.4.1.mtd', '/root/sn20fw/obmc/obmc-3.4.1.mtd.md5'], '/dev/shm', ip, host_port=host_port)
            # send_file(, '/dev/shm', ip, host_port=host_port)

        thread_xrdus(ports, 'obmcupdate -p recovery -t bmc -f /dev/shm/obmc-3.4.1.mtd; date')

    print('************************************************\n RDUC Files\n************************************************')

    for ip in ips:
        # Update RDUC
        send_files(['/root/sn20fw/rduc/rduc-4.4.1-override.spi', 
        '/root/sn20fw/rduc/rduc-4.4.1-override.spi.md5', 
        '/root/sn20fw/rduc/rduc-4.4.1-primary.spi', 
        '/root/sn20fw/rduc/rduc-4.4.1-primary.spi.md5', 
        '/root/sn20fw/rduc/rduc-4.4.1-recovery.spi', 
        '/root/sn20fw/rduc/rduc-4.4.1-recovery.spi.md5'], '/dev/shm', ip, host_port=host_port)
        # send_file(, '/dev/shm', ip, host_port=host_port)

        # send_file('/root/sn20fw/rduc/rduc-4.4.1-primary.spi', '/dev/shm', ip, host_port=host_port)
        # send_file('/root/sn20fw/rduc/rduc-4.4.1-primary.spi.md5', '/dev/shm', ip, host_port=host_port)
        
        # send_file('/root/sn20fw/rduc/rduc-4.4.1-recovery.spi', '/dev/shm', ip, host_port=host_port)
        # send_file('/root/sn20fw/rduc/rduc-4.4.1-recovery.spi.md5', '/dev/shm', ip, host_port=host_port)
    
    print('************************************************\n RDUC Primary Partition Override\n************************************************')
    thread_xrdus(ports, 'obmcupdate -p primary -t rduc -f /dev/shm/rduc-4.4.1-override.spi')
    print('************************************************\n RDUC Primary Partition Primary\n************************************************')
    thread_xrdus(ports, 'obmcupdate -p primary -t rduc -f /dev/shm/rduc-4.4.1-primary.spi')
    print('************************************************\n RDUC Recovery Partition\n************************************************')
    thread_xrdus(ports, 'obmcupdate -p recovery -t rduc -f /dev/shm/rduc-4.4.1-recovery.spi')

    end = datetime.datetime.now()
    print(f'Debug: {start} -> {end}')
    print(f'Debug: Total Time: {end - start}')

def thread_xrdus(ports, command):
    threads = []

    for port in ports:
        threads.append(threading.Thread(target=remote_watch_command, kwargs={'port': port, 'command': command}))
    
    print('Threads Created')

    for thread in threads:
        thread.start()

    print('Threads Started')

    for thread in threads:
        thread.join()
    
    print('jobs done')


def remote_watch_command(port, command):
    current_xrdu = {
        "device_type": "terminal_server",
        "host": "10.70.10.7",
        "username": "root",
        "password": "Changeme",
        "port": port
    }

    xrdu_ssh = ConnectHandler(**current_xrdu)

    prompt = xrdu_ssh.find_prompt()
    print(f'Port {port} RX: {prompt}')
        
    output = ''

    if('login:' in prompt):
        xrdu_ssh.write_channel('root\n')
        while('password:' not in output.lower()):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')

        xrdu_ssh.write_channel('0penBmc\n')
        output = ''
        while('snservice@' not in output and 'root@' not in output and 'login:' not in output):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')
        
    if('login:' in output):
        xrdu_ssh.write_channel('root\n')
        while('password:' not in output.lower()):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')
        xrdu_ssh.write_channel('1Changeme\n')

        while('snservice@' not in output and 'root@' not in output and 'login:' not in output):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')

    print(f'Port {port} TX: {command}')
    time.sleep(1)
    xrdu_ssh.write_channel(f'{command}\n')
    output = ''
    while(prompt not in output and 'login:' not in output):
        output = xrdu_ssh.read_channel()
        time.sleep(1)
        if output and not re.search(r'((Erasing block|Writing kb|Verifying kb): \d+\/(2048|131072) \(\d{1,2}%\))', output):
            print(f'Port {port} RX: {output}')
    
    if('login:' in output):
        xrdu_ssh.write_channel('root\n')
        while('password:' not in output.lower()):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')

        xrdu_ssh.write_channel('0penBmc\n')
        output = ''
        while('snservice@' not in output and 'root@' not in output and 'login:' not in output):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output and not re.search(r'((Erasing block|Writing kb|Verifying kb): \d+\/(2048|131072|4096) \(\d{1,2}%\))|(obmc-3.4.1.mtd\s+\d{1,2}%\s+\d{1,2}(MB)?\s+\d\.\d(M|K)B\/s\s+.+\sETA)|(\[=+\] \d{1,2}%)', output):
                print(f'Port {port} RX: {output}')

    if('login:' in output):
        xrdu_ssh.write_channel('root\n')
        while('password:' not in output.lower()):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')
        xrdu_ssh.write_channel('1Changeme\n')

        while('snservice@' not in output and 'root@' not in output and 'login:' not in output):
            output = xrdu_ssh.read_channel()
            time.sleep(1)
            if output:
                print(f'Port {port} RX: {output}')

    xrdu_ssh.disconnect()

def rm_ssh_hosts(host_port):
    debug_host = {
        "device_type": "linux",
        "host": "10.70.10.7",
        "username": "root",
        "password": "Changeme",
        "port": host_port
    }

    debug_ssh = ConnectHandler(**debug_host)
    prompt = debug_ssh.find_prompt()
    print(f'RX: {prompt}')

    print(f'TX: rm ~/.ssh/known_hosts')
    output = debug_ssh.send_command('rm ~/.ssh/known_hosts')
    print(f'RX: {output}')


def send_files(files, location, ip, host_port):
    debug_host = {
        "device_type": "linux",
        "host": "10.70.10.7",
        "username": "root",
        "password": "Changeme",
        "port": host_port,
        "global_delay_factor": 10
    }

    debug_ssh = ConnectHandler(**debug_host)

    prompt = debug_ssh.find_prompt()
    print(f'RX: {prompt}')

    for cfile in files:
        print(f'TX: /usr/bin/scp {cfile} {ip}:{location}')
        # output = debug_ssh.send_command('/usr/bin/scp sda1-partition root@192.168.10.7:/root', expect_string='(yes/no/[fingerprint])? ')
        debug_ssh.write_channel(f'/usr/bin/scp {cfile} {ip}:{location}\n')
        time.sleep(1)
        output = debug_ssh.read_until_pattern(r'\(yes\/no\/\[fingerprint\]\)\?|password:')
        print(f'RX: {output}')

        if('password:' not in output):
            print(f'TX: yes')
            output = debug_ssh.send_command('yes', expect_string='password')
            print(f'RX: {output}')

        print(f'TX: 0penBmc')
        print(f'DEBUG: {datetime.datetime.now()}')
        # output = debug_ssh.send_command('0penBmc', expect_string=prompt, cmd_verify=False)
        debug_ssh.write_channel('0penBmc\n')
        output = ''
        while(prompt not in output and 'password' not in output):
            output = debug_ssh.read_channel()
            time.sleep(1)
            print(f'RX: {output}')

        if 'password' in output:
            print(f'TX: 1Changeme')
            debug_ssh.write_channel('1Changeme\n')
            output = ''
            while(prompt not in output and 'password' not in output):
                output = debug_ssh.read_channel()
                time.sleep(1)
                print(f'RX: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog = 'setup_batch.py',
    )

    update_batch(0, skip_obmc_primary=False, skip_obmc_recovery=False)


