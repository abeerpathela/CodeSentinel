import subprocess

def get_python_version():
    return subprocess.run(
        ["python", "--version"],
        capture_output=True,
        text=True,
        shell=False
    ).stdout
