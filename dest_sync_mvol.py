import boto3
import os
import concurrent.futures
import pandas as pd
import time
from helper import read_config, list_objects, get_all_local_files
import json

def main():
    # Read data from JSON file
    with open('failed_endpoints.json', 'r') as file:
        data = json.load(file)

    # Extract values
    failed_dest_endpoints = data["failed_dest_endpoints"]

    def execute_command(command):
        os.system(command)

    config = read_config()
    
    if not config:
        print("Failed to read the configuration.")
        return

    # set up available volumes
    # base_path = "/tmp/volume-"
    base_path = "/home/leafmanznotel/volume-"
    volumes = [base_path + str(i).zfill(2) for i in range(1, 100) if os.path.exists(base_path + str(i).zfill(2))]

    # set up destination information
    bucket_dest_name = config["destination"]["bucket_name"]
    bucket_dest_prefix = config["destination"]["bucket_prefix"]
    bucket_dest_region = config["destination"]["region"]
    access_key_dest = config["destination"]["access_key"]
    secret_access_key_dest = config["destination"]["secret_access_key"]

    # set up destination s3 url
    dest_endpoint_urls = config["transfer_settings"]["dest_endpoint_url"]
    dest_endpoint_urls = [url for url in dest_endpoint_urls if url not in failed_dest_endpoints]

    if dest_endpoint_urls[0] == 'no_endpoint':
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region)
    elif 's3-accelerate' in dest_endpoint_urls[0] and bucket_dest_region != 'snow':
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region)
    elif dest_endpoint_urls[0] != 'no_endpoint' and bucket_dest_region != 'snow':
        # create aws clients to see destination objects
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region, 
        endpoint_url=dest_endpoint_urls[0], 
        use_ssl=False, verify=False)
    else:
        # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
        session = boto3.Session(
            aws_access_key_id=access_key_dest, 
            aws_secret_access_key=secret_access_key_dest
        )

        # Connect to S3 with the specified endpoint
        if 'https' in dest_endpoint_urls[0]: # denotes new snowballs
            s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_urls[0], verify=False)
        else:
            s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_urls[0])

    while True:
        # get the objects in our destination bucket and volumes to compare missing objects and sync them from local to destination
        objects_in_dest = list_objects(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow'))
        local_files = get_all_local_files(volumes, include_volumes=True)

        dest_difference = {key:vol for vol, files in local_files.items() for key in files if (key not in objects_in_dest or files[key] != objects_in_dest[key])}

        num_files = len(dest_endpoint_urls)
        items_per_file = len(dest_difference) // num_files
        remaining_items = len(dest_difference) % num_files

        # Prepare to split the items across the destination command files
        items_for_each_file = [items_per_file + (1 if i < remaining_items else 0) for i in range(num_files)]
        items_iter = iter(dest_difference.items())

        dest_commands = []
        for dest_endpoint_url_idx in range(num_files):
            # Clear the content of dest_commands.txt before writing
            with open(f'dest_commands_{dest_endpoint_url_idx}.txt', 'w') as file:
                pass

            if dest_difference:
                with open(f'dest_commands_{dest_endpoint_url_idx}.txt', 'w') as file:
                    for _ in range(items_for_each_file[dest_endpoint_url_idx]):
                        obj_key, obj_vol = next(items_iter)
                        dest_path = f"s3://{bucket_dest_name}/{bucket_dest_prefix}{obj_key}"
                        local_path = f"{obj_vol}/{obj_key}"

                        command = f"cp --concurrency 15 --destination-region {bucket_dest_region} '{local_path}' '{dest_path}'"
                        file.write(command + '\n')
                print(f"Commands have been written to dest_commands_{dest_endpoint_url_idx}.txt.")

                # Setting up AWS environment variables to use s5cmd to move from source to local
                os.environ["AWS_ACCESS_KEY_ID"] = access_key_dest
                os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key_dest

                # Execute the shell dest_command
                if dest_endpoint_urls[dest_endpoint_url_idx] == 'no_endpoint':
                    dest_command = f"time ./s5cmd --stat --numworkers 64 run dest_commands_{dest_endpoint_url_idx}.txt"
                else:
                    verify_ssl = '--no-verify-ssl' if 'https' in dest_endpoint_urls[dest_endpoint_url_idx] else ''
                    dest_command = f"time ./s5cmd --stat --endpoint-url={dest_endpoint_urls[dest_endpoint_url_idx]} {verify_ssl} --numworkers 64 run dest_commands_{dest_endpoint_url_idx}.txt"
                dest_commands.append(dest_command)
            else:
                print(f"All objects in {bucket_dest_name}/{bucket_dest_prefix} are identical in {volumes}.")
        
        # Use ThreadPoolExecutor to execute commands concurrently
        if dest_commands:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(dest_commands)) as executor:
                futures = [executor.submit(execute_command, cmd) for cmd in dest_commands]
                for future in concurrent.futures.as_completed(futures):
                    print(f"Command executed with return code: {future.result()}")
        else:
            print("No commands to execute.")

        dest_same = {key:vol for vol, files in local_files.items() for key in files if key in objects_in_dest and files[key] == objects_in_dest[key]}

        # only save keys that are in dest_same (marked for deletion) and keys that are in src_ledger_df
        src_ledger_df = pd.read_csv('src_ledger.csv')
        dest_same_ledger = {obj_key: obj_vol for obj_key, obj_vol in dest_same.items() if obj_key in list(src_ledger_df['Key'])}

        for obj_key, obj_vol in dest_same_ledger.items():
            try:
                os.remove(f"{obj_vol}/{obj_key}")
            except Exception as e:
                print(f"Error removing file {obj_vol}/{obj_key}: {e}")
                
        print('Waiting 1 second before checking for new additions of data in the source bucket.')
        time.sleep(1)

        with open('sync_progress.json', 'r') as file:
            sync_data = json.load(file)
        
        if 'Completed' in sync_data['Status']:
            break
    
    print('ALL FILES FROM STAGING HAVE COMPLETED MOVING.')
    print('dest_sync_mvol.py has stopped.')
    print('PLEASE RUN repair_ledger.py to verify data integrity.')

if __name__ == "__main__":
    main()

