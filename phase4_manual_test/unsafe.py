import subprocess

def execute():
    command = input("Command: ")

    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
