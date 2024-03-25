import subprocess
import json

def get_disks_without_partitions():
    # Execute lsblk to get the list of devices in JSON format
    result = subprocess.run(['lsblk', '-J', '-o', 'NAME,TYPE'], capture_output=True, text=True)
    
    # Check if the command was executed successfully
    if result.returncode != 0:
        print("Error executing lsblk command")
        return
    
    # Parse the JSON output
    output = json.loads(result.stdout)
    
    get_disks_without_partitions = []
    # Iterate through the devices and find disks without partitions
    for device in output.get('blockdevices', []):
        if device['type'] == 'disk' and not device.get('children'):
            # Print the name of the disk without partitions
            get_disks_without_partitions.append(device['name'])
    return get_disks_without_partitions

def format_disk_as_ext4(disk):
    try:
        # Using subprocess.run to execute the command
        # Note: subprocess.run is available in Python 3.5+
        result = subprocess.run(['sudo', 'mkfs.ext4', f'/dev/{disk}'], text=True, input='y', capture_output=True)
        if result.returncode == 0:
            print(f"Disk /dev/{disk} formatted successfully.")
        else:
            print(f"Error formatting disk /dev/{disk}: {result.stderr}")
    except Exception as e:
        print(f"Exception occurred: {e}")

def create_and_mount(disk, directory):
    try:
        # Create directory
        subprocess.run(['mkdir', '-p', directory], check=True)
        
        # Mount the disk to the directory
        subprocess.run(['sudo', 'mount', f'/dev/{disk}', directory], check=True)
        
        # Change directory permissions to 777
        subprocess.run(['sudo', 'chmod', '777', directory], check=True)
        
        print(f"Disk /dev/{disk} mounted successfully to {directory} with permissions set to 777.")
    except subprocess.CalledProcessError as e:
        print(f"Error during creation, mounting, or changing permissions: {e}")

if __name__ == '__main__':
    disks_without_partitions = get_disks_without_partitions()
    volume_counter = 1
    for disk in disks_without_partitions:
        format_disk_as_ext4(disk)
        # Create a directory and mount the disk
        directory = f'/tmp/volume-{volume_counter:02}'
        create_and_mount(disk, directory)
        volume_counter += 1