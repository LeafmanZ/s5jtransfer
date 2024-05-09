import os
import shutil
from helper import read_config
import pandas as pd

def delete_contents(path):
    """
    Deletes all contents of a given directory without deleting the directory itself.
    """
    for item in os.listdir(path):
        if "lost+found" == item:
            continue
        
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

def delete_volume_contents():
    # base_dir = '/tmp'
    base_dir = '/home/leafmanznotel'
    if os.path.exists(base_dir):
        for dir_name in os.listdir(base_dir):
            if dir_name.startswith('volume-') and dir_name[7:].isdigit():
                full_dir_path = os.path.join(base_dir, dir_name)
                if os.path.isdir(full_dir_path):
                    delete_contents(full_dir_path)
                    print(f"Deleted contents of {full_dir_path}")

# Check and remove file if it exists
def safe_remove(file_path):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            print(f"Failed to remove {file_path} probably not a big deal.")

# Main execution
if __name__ == "__main__":
    # Remove files if they exist
    safe_remove('src_commands.txt')
    safe_remove('dest_ledger.csv')
    safe_remove('src_ledger.csv')

    df = pd.DataFrame(columns=['Key', 'Size'])
    df.to_csv('src_ledger.csv', index=False)

    config = read_config()

    if not config:
        print("Failed to read the configuration.")

    for i in range(max(len(config["transfer_settings"]["dest_endpoint_url"]), 10)):
        safe_remove(f'dest_commands_{i}.txt')

    # Remove directory if it exists and then create it
    if os.path.exists(config["local"]["directory"]):
        shutil.rmtree(config["local"]["directory"])
    os.mkdir(config["local"]["directory"])

    # Delete contents of volume directories in /tmp
    delete_volume_contents()

