import yaml
import os
import subprocess
import re
import signal

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

def read_config(filename="config.yaml"):
    with open(filename, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return None

def test_endpoint(bucket_name, prefix, s3_client, isSnow=False, timeout=5):
    """List all objects in a given bucket with a specified prefix along with their size, with a timeout."""
    """Returns True if endpoint is good, Returns False if endpoint is bad."""
    def inner():
        if isSnow:
            return list_objects_sbe(bucket_name, prefix, s3_client)

        objects = {}
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    if not obj["Key"].endswith('/'):
                        key = obj["Key"].replace(prefix, '', 1)
                        objects[key] = obj['Size']
            break
        return True

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)  # Set the timeout
    try:
        result = inner()
    except Exception as e:
        return False
    finally:
        signal.alarm(0)  # Disable the alarm

    return result

def list_objects(bucket_name, prefix, s3_client, isSnow=False):
    """List all objects in a given bucket with a specified prefix along with their size."""
    if isSnow:
        return list_objects_sbe(bucket_name, prefix, s3_client)

    objects = {}
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                if not obj["Key"].endswith('/'):
                    key = obj["Key"].replace(prefix, '', 1)
                    objects[key] = obj['Size']
    return objects

def list_objects_sbe(bucket_name, prefix, s3_client):
    """List all objects in a given bucket with a specified prefix along with their size."""
    objects = {}

    # Get the bucket instance
    bucket = s3_client.Bucket(bucket_name)

    # List all the objects in the bucket with the given prefix
    for obj in bucket.objects.filter(Prefix=prefix):
        if not obj.key.endswith('/'):
            key = obj.key.replace(prefix, '', 1)
            objects[key] = obj.size
    return objects

def get_local_files(directory):
    """Return a dictionary with local file names as keys and their sizes as values, 
    excluding files whose extensions end with two or more numbers, but including 
    those ending with an underscore followed by one or two digits."""
    local_files = {}

    # Pattern to match files whose extensions end with two or more numbers, 
    # excluding an underscore followed by 1 or 2 digits
    pattern = re.compile(r'\b[0-9a-fA-F]+\b') # S3 incomplete file
    pattern2= re.compile(r'\d{4,}$') # S5cmd incomplete file
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # If file matches pattern, skip it
            if pattern.search(file[file.rindex('.'):]) or pattern2.search(file[file.rindex('.'):]):
                continue
            
            path = os.path.join(root, file)
            relative_path = os.path.relpath(path, directory)
            local_files[relative_path] = os.path.getsize(path)
    
    return local_files

def get_disk_usage(directory):
    result = subprocess.run(['df', directory], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    if len(lines) > 1:
        parts = lines[1].split()
        if len(parts) >= 5:
            return {
                'filesystem': parts[0],
                'total': int(parts[1]),
                'used': int(parts[2]),
                'available': int(parts[3]),
                'use_percentage': parts[4],
                'mounted_on': parts[5]
            }
    return None

def get_all_local_files(volumes, include_volumes=False):
    all_files = {}
    for volume in volumes:
        if include_volumes:
            all_files[volume] = get_local_files(volume)
        else:
            all_files.update(get_local_files(volume))
    return all_files
