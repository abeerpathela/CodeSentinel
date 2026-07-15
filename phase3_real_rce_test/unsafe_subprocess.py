import subprocess

def execute_command():
    user_command = input("Enter command: ")

    return subprocess.run(
        user_command,
        shell=True,
        capture_output=True,
        text=True
    )
