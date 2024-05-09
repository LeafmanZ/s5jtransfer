import boto3
import os
import subprocess
import concurrent.futures
import pandas as pd
import time
from helper import read_config, list_objects, get_disk_usage, get_all_local_files
import json

def main():

    # Read data from JSON file
    with open('failed_endpoints.json', 'r') as file:
        failed_endpoints_data = json.load(file)

    # Extract values
    failed_src_endpoints = failed_endpoints_data["failed_src_endpoints"]

    config = read_config()

    if not config:
        print("Failed to read the configuration.")
        return

    # set up source information
    bucket_src_name = config["source"]["bucket_name"]
    bucket_src_prefix = config["source"]["bucket_prefix"]
    bucket_src_region = config["source"]["region"]
    access_key_src = config["source"]["access_key"]
    secret_access_key_src = config["source"]["secret_access_key"]

    # set up source s3 url
    src_endpoint_urls = config["transfer_settings"]["src_endpoint_url"]
    src_endpoint_urls = [url for url in src_endpoint_urls if url not in failed_src_endpoints]

    src_use_native_s3 = config["transfer_settings"]["src_use_native_s3"]

    if src_endpoint_urls[0] == 'no_endpoint':
        s3_client_src = boto3.client('s3', 
        aws_access_key_id=access_key_src, 
        aws_secret_access_key=secret_access_key_src, 
        region_name=bucket_src_region)
    elif src_endpoint_urls[0] != 'no_endpoint' and bucket_src_region != 'snow': 
        # create aws clients to see source objects
        s3_client_src = boto3.client('s3', 
        aws_access_key_id=access_key_src, 
        aws_secret_access_key=secret_access_key_src, 
        region_name=bucket_src_region, 
        endpoint_url=src_endpoint_urls[0],
        use_ssl=False, verify=False)
    else:
        # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
        session = boto3.Session(
            aws_access_key_id=access_key_src, 
            aws_secret_access_key=secret_access_key_src
        )

        # Connect to S3 with the specified endpoint
        if 'https' in src_endpoint_urls[0]: # denotes new snowballs
            s3_client_src = session.resource('s3', endpoint_url=src_endpoint_urls[0], verify=False)
        else:
            s3_client_src = session.resource('s3', endpoint_url=src_endpoint_urls[0])

    # set up available volumes
    # base_path = "/tmp/volume-"
    base_path = "/home/leafmanznotel/volume-"
    volumes = [base_path + str(i).zfill(2) for i in range(1, 100) if os.path.exists(base_path + str(i).zfill(2))]

    # set up maximum data transfer amount per run from source edge s3 to localstore
    # need to divide this by number of volumes
    max_size_to_transfer_src2l = int(config["transfer_settings"]["max_size_to_transfer_src2l"])

    # Get the objects in our source bucket and volumes to compare missing objects and sync them from source to local
    objects_in_src = list_objects(bucket_src_name, bucket_src_prefix, s3_client_src, isSnow=(bucket_src_region=='snow'))
    local_files = get_all_local_files(volumes)

    # Get keys in S3 bucket not in local or with different sizes, also checks if the keys have already been moved as recorded in the source ledger
    if os.path.isfile('src_ledger.csv'):
        src_ledger_df = pd.read_csv('src_ledger.csv')
        src_difference = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key]) and (key not in src_ledger_df['Key'].values)}
    else:
        src_difference = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key])}

    data = []
    if src_difference:
        data = [(key, objects_in_src[key]) for key in src_difference]
        data.sort(key=lambda x: x[1], reverse=True)  # Sort descending by size
    else:
        print(f"All objects in {bucket_src_name}/{bucket_src_prefix} are identical in {volumes}. Or all objects that can possibly be moved to {volumes} have been moved.")
        print('Waiting 1 second before checking for new additions of data in the source bucket.')
        time.sleep(1)

    while True:
        volume_usages = {volume: get_disk_usage(volume) for volume in volumes}
        
        available_space_per_volume = {
            volume: min(int(usage['available'] * .09 * 10000), max_size_to_transfer_src2l) for volume, usage in volume_usages.items() if usage
        }

        # Clear the content of src_commands.txt before writing
        with open('src_commands.txt', 'w') as file:
            pass

        # Setting up AWS environment variables to use s5cmd to move from source to local
        os.environ["AWS_ACCESS_KEY_ID"] = access_key_src
        os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key_src

        recent_batch_data = []
        available_space_per_volume_keys = list(available_space_per_volume.keys())

        if src_use_native_s3:
            with open('src_commands.txt', 'a') as file:
                for data_idx in range(len(data)):
                    obj_key, obj_size = data[data_idx]
                    
                    volume_idx = (data_idx) % len(available_space_per_volume)
                    endpoint_idx = (data_idx) % len(src_endpoint_urls)
                    
                    space_left = available_space_per_volume[available_space_per_volume_keys[volume_idx]] - obj_size
                    if space_left > 0:
                        available_space_per_volume[available_space_per_volume_keys[volume_idx]] = space_left
                        src_path = f"s3://{bucket_src_name}/{bucket_src_prefix}{obj_key}"
                        dst_path = f"{available_space_per_volume_keys[volume_idx]}/{obj_key}"
                        
                        if src_endpoint_urls[endpoint_idx] == 'no_endpoint': # likely using normal cloud s3 bucket
                            command = f"aws s3 cp '{src_path}' '{dst_path}' --region {bucket_src_region}"
                        elif src_endpoint_urls[endpoint_idx] != 'no_endpoint' and bucket_src_region != 'snow': # likely using transfer accelerator
                            command = f"aws s3 cp '{src_path}' '{dst_path}' --region {bucket_src_region} --endpoint-url={src_endpoint_urls[endpoint_idx]} --no-verify-ssl"
                        else:
                            if 'https' in src_endpoint_urls[endpoint_idx]: # denotes new snowball s3
                                command = f"aws s3 cp '{src_path}' '{dst_path}' --region {bucket_src_region} --endpoint-url={src_endpoint_urls[endpoint_idx]} --no-verify-ssl"
                            else: # denotes old snowball s3
                                command = f"aws s3 cp '{src_path}' '{dst_path}' --region {bucket_src_region} --endpoint-url={src_endpoint_urls[endpoint_idx]}"
                        file.write(command + '\n')
                    else:
                        del available_space_per_volume[available_space_per_volume_keys[volume_idx]]
                        available_space_per_volume_keys.remove(available_space_per_volume_keys[volume_idx])
                        data_idx = data_idx - 1

                    recent_batch_data.append((obj_key, obj_size))
                    if not available_space_per_volume:
                        break

            print(f"Commands have been written to src_commands.txt.")

            def execute_command(command):
                try:
                    subprocess.run(command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    
                    # Handle the exception (e.g., log the error)
                    print(f"Command failed: {command}\nError: {e}")
    
            # Read the commands from the file
            with open('src_commands.txt', 'r') as file:
                commands = [command.strip() for command in file.readlines()]

            # Use ThreadPoolExecutor to execute the commands concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(volumes)) as executor:
                # Map the execute_command function to each command
                futures = [executor.submit(execute_command, command) for command in commands]

                # Wait for all futures to complete
                concurrent.futures.wait(futures)
        else:
            with open('src_commands.txt', 'a') as file:
                for data_idx in range(len(data)):
                    obj_key, obj_size = data[data_idx]
                    
                    volume_idx = (data_idx) % len(available_space_per_volume)
                    
                    space_left = available_space_per_volume[available_space_per_volume_keys[volume_idx]] - obj_size
                    if space_left > 0:
                        available_space_per_volume[available_space_per_volume_keys[volume_idx]] = space_left
                        src_path = f"s3://{bucket_src_name}/{bucket_src_prefix}{obj_key}"
                        dst_path = f"{available_space_per_volume_keys[volume_idx]}/{obj_key}"
                        
                        command = f"cp --concurrency 5 --source-region {bucket_src_region} '{src_path}' '{dst_path}'"
                        file.write(command + '\n')
                    else:
                        del available_space_per_volume[available_space_per_volume_keys[volume_idx]]
                        available_space_per_volume_keys.remove(available_space_per_volume_keys[volume_idx])
                        data_idx = data_idx - 1

                    recent_batch_data.append((obj_key, obj_size))
                    if not available_space_per_volume:
                        break
                    
            print(f"Commands have been written to src_commands.txt.")
            
            # Execute the shell src_command
            if src_endpoint_urls[0] == 'no_endpoint': # likely using normal cloud s3 bucket
                src_command = "time ./s5cmd --stat --numworkers 64 run src_commands.txt"
            elif src_endpoint_urls[0] != 'no_endpoint' and bucket_src_region != 'snow': # likely using transfer accelerator
                src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_urls[0]} --no-verify-ssl --numworkers 64 run src_commands.txt"
            else:
                if 'https' in src_endpoint_urls[0]: # denotes new snowball s3
                    src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_urls[0]} --no-verify-ssl --numworkers 64 run src_commands.txt"
                else: # denotes old snowball s3
                    src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_urls[0]} --numworkers 64 run src_commands.txt"
            os.system(src_command)

        # Continue with the rest of your script
        print("All commands have completed.")

        current_run_src_ledger_df = pd.DataFrame(recent_batch_data, columns=['Key', 'Size'])

        # If CSV doesn't exist, write the header, otherwise skip
        if not os.path.isfile('src_ledger.csv'):
            current_run_src_ledger_df.to_csv('src_ledger.csv', index=False)
        else:
            current_run_src_ledger_df.to_csv('src_ledger.csv', mode='a', header=False, index=False)
        
        data = data[len(recent_batch_data):]
            
        print('Objects set to move have been recorded to src_ledger.csv')
        print('Waiting 1 second before checking for new additions of data in the source bucket.')
        time.sleep(1)

        if len(data) <= 0:
            os.system('python repair_ledger.py')

        with open('sync_progress.json', 'r') as file:
            sync_data = json.load(file)
        
        if 'Completed' in sync_data['Status']:
            break

    print('ALL FILES FROM SOURCE HAVE COMPLETED MOVING.')
    print('src_sync_mvol.py has stopped.')
    print('PLEASE RUN repair_ledger.py to verify data integrity.')

if __name__ == "__main__":
    main()