import subprocess

def get_python_version():
    result = subprocess.run(
        ["python", "--version"],
        capture_output=True,
        text=True,
        shell=False
    )

    return result.stdout
