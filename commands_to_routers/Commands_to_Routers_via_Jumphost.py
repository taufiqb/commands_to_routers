import paramiko
import time
import logging
import csv

def read_routers_from_file(file_path):
    routers = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 2:
                routers.append((row[0].strip(), row[1].strip()))
    return routers

def read_commands_from_file(file_path):
    with open(file_path, 'r') as file:
        commands = [line.strip() for line in file if line.strip()]
    return commands

def ssh_connect(hostname, username, password, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password, timeout=timeout)
    return ssh

def ssh_command(shell, command):
    shell.send(command + "\n")
    time.sleep(2)
    output = ""
    while shell.recv_ready():
        output += shell.recv(65535).decode('utf-8')
    return output

def interactive_ssh(ssh, router_username, router_password):
    shell = ssh.invoke_shell()
    time.sleep(1)
    
    if shell.recv_ready():
        output = shell.recv(65535).decode()
        print("Router Prompt (before username):", output)

    shell.send(f"{router_username}\n")
    time.sleep(1)
    
    if shell.recv_ready():
        output = shell.recv(65535).decode()
        print("Router Prompt (before password):", output)

    shell.send(f"{router_password}\n")
    time.sleep(1)
    
    if shell.recv_ready():
        output = shell.recv(65535).decode()
        print("Router Prompt (after password):", output)

    return shell

def main():
    logging.basicConfig(filename="router_log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")
    
    jump_host = "jump_host ip address"
    jump_username = "my_jh_user_name"
    jump_password = "my_jh_password"
    
    router_username = "my_router_usr_name"
    router_password = "my_router_password"
    
    routers_file_path = "list_of_routers.csv"
    commands_file_path = "commands.txt"
    output_file_path = "router_outputs.txt"
    
    routers = read_routers_from_file(routers_file_path)
    commands = read_commands_from_file(commands_file_path)
    
    print(f"Connecting to the jumphost: {jump_host}")
    try:
        jump_ssh = ssh_connect(jump_host, jump_username, jump_password)
        print("Connected to the jumphost.")
    except Exception as e:
        print(f"Failed to connect to the jumphost: {e}")
        logging.error(f"Failed to connect to the jumphost: {e}")
        return
    
    try:
        with open(output_file_path, 'w') as output_file:
            for router_name, router_ip in routers:
                try:
                    print(f"Connecting to router: {router_name} ({router_ip})")
                    logging.info(f"Connecting to router: {router_name} ({router_ip})")
                    
                    router_ssh = jump_ssh.invoke_shell()
                    router_ssh.send(f"ssh {router_username}@{router_ip}\n")
                    time.sleep(2)
                    
                    router_ssh.send(router_password + "\n")
                    time.sleep(2)
                    
                    output = ""
                    while not router_ssh.recv_ready():
                        time.sleep(1)
                    output += router_ssh.recv(65535).decode('utf-8')
                    if "> " in output:
                        print(f"Successfully logged into router: {router_name}")
                        logging.info(f"Successfully logged into router: {router_name}")
                    else:
                        raise Exception("Router login failed. Check credentials or connectivity.")
                    
                    output_file.write(f"Router: {router_name} ({router_ip})\n")
                    for command in commands:
                        print(f"Executing command on {router_name}: {command}")
                        logging.info(f"Executing command on {router_name}: {command}")
                        command_output = ssh_command(router_ssh, command)
                        output_file.write(f"\nCommand: {command}\n")
                        output_file.write(command_output)
                        output_file.write("\n" + "-"*40 + "\n")
                    
                    router_ssh.send("exit\n")
                    time.sleep(1)
                    print(f"Logged out from router: {router_name}")
                    logging.info(f"Logged out from router: {router_name}")
                
                except Exception as e:
                    print(f"Failed to connect to {router_name} ({router_ip}): {e}")
                    logging.error(f"Failed to connect to {router_name} ({router_ip}): {e}")
                    output_file.write(f"Failed to connect to {router_name} ({router_ip}): {e}\n")
    
    finally:
        jump_ssh.close()
        print("Closed connection to the jumphost.")
        logging.info("Closed connection to the jumphost.")

if __name__ == '__main__':
    main()