import subprocess
import asyncio
from pathlib import Path
from debug_logger import DebugLogger

initial_run_sha = None

def set_initial_run_sha():
    global initial_run_sha
    initial_run_sha = get_latest_local_commit_sha()
    print(f"Initial run sha: {initial_run_sha}")

    debug_logger = DebugLogger.get_instance()
    debug_logger.log(f"Initial run sha: {initial_run_sha}")

def get_latest_local_commit_sha():
    try:
        commit_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except subprocess.CalledProcessError as e:
        print(f'An error occurred while trying to fetch the latest local commit SHA: {str(e)}')
        return None
    return commit_sha

def get_latest_remote_commit_sha():
    try:
        subprocess.check_output(['git', 'fetch'], text=True)
        commit_sha = subprocess.check_output(['git', 'rev-parse', 'origin/main'], text=True).strip()
    except subprocess.CalledProcessError as e:
        print(f'An error occurred while trying to fetch the latest remote commit SHA: {str(e)}')
        return None
    return commit_sha

async def check_version(bot):
    global initial_run_sha
    check_sha = get_latest_remote_commit_sha()

    if check_sha and initial_run_sha != check_sha:
        debug_logger = DebugLogger.get_instance()
        debug_logger.log(f"[New Version Detected] 🥳 Initiating the update and restart process... [{initial_run_sha[:7]}] -> [{check_sha[:7]}]")
        try:
            await debug_logger.flush()
            await asyncio.sleep(1)
            await bot.close()
        except:
            pass

def backup_to_github():
    debug_logger = DebugLogger.get_instance()
    debug_logger.log("Uploading user data to backup repository...")

    # Relative paths assuming script is run from a specific root directory
    root_folder = Path.cwd()
    source_folder = root_folder / "data"
    dest_folder = root_folder.parent / "TLERepBotData"

    # Using rsync to copy directory to ensure it only copies the changes.
    command = ["xcopy", str(source_folder) + "\\*", str(dest_folder), "/E", "/Y", "/I", "/D"]
    debug_logger.log(f"{command}")
    subprocess.run(command)

    # Delete data/debugconf.yaml in the destination folder
    debugconf_path = dest_folder / "debugconf.yaml"
    if debugconf_path.exists():
        debugconf_path.unlink()

    # Stage, commit, and push changes to GitHub repository
    subprocess.run(["git", "-C", str(dest_folder), "add", "-A"])
    subprocess.run(["git", "-C", str(dest_folder), "commit", "-m", "Backup data"])
    subprocess.run(["git", "-C", str(dest_folder), "push"])

    debug_logger.log("Upload complete.")


# Code below uses the GitHub API to check for updates and restart the bot if there is a new version.
# import requests
# import asyncio
# from _secrets import GITHUB_TOKEN, GITHUB_COMMIT_URL
# from debug_logger import DebugLogger

# initial_run_sha = 0

    
# def set_initial_run_sha():
#     global initial_run_sha
#     initial_run_sha = get_latest_commit_sha()
#     print(f"Initial run sha: {initial_run_sha}")

#     debug_logger = DebugLogger.get_instance()
#     debug_logger.log(f"Initial run sha: {initial_run_sha}")

# def get_latest_commit_sha():
#     url = GITHUB_COMMIT_URL
#     headers = {
#         "Authorization": f"token {GITHUB_TOKEN}",
#     }
#     response = requests.get(url, headers=headers)

#     if response.status_code == 200:
#         commits = response.json()
#         latest_commit = commits[0]
#         full_sha = latest_commit["sha"]
#         short_sha = full_sha[:7]
        
#         return short_sha
#     else:
#         print(f"Error: {response.status_code}")
#         return None

# async def check_version(bot):
#     global initial_run_sha
#     check_sha = get_latest_commit_sha()

#     if not check_sha.startswith('Error') and initial_run_sha != check_sha:
#         debug_logger = DebugLogger.get_instance()
#         debug_logger.log(f"[New Version Detected] 🥳 Initiating the update and restart process... [{initial_run_sha}] -> [{check_sha}]")
#         try:
#             await debug_logger.flush()
#             await asyncio.sleep(1)
#             await bot.close()
#         except:
#             pass