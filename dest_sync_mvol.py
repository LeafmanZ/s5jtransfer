import boto3
import os
import pandas as pd
import time
from helper import read_config, list_objects, get_all_local_files

def main():
    config = read_config()
    
    if not config:
        print("Failed to read the configuration.")
        return

    # set up available volumes
    base_path = "/tmp/volume-"
    volumes = [base_path + str(i).zfill(2) for i in range(1, 100) if os.path.exists(base_path + str(i).zfill(2))]

    # set up destination information
    bucket_dest_name = config["destination"]["bucket_name"]
    bucket_dest_prefix = config["destination"]["bucket_prefix"]
    bucket_dest_region = config["destination"]["region"]
    access_key_dest = config["destination"]["access_key"]
    secret_access_key_dest = config["destination"]["secret_access_key"]

    # set up destination s3 url
    dest_endpoint_url = config["transfer_settings"]["dest_endpoint_url"]

    if dest_endpoint_url == 'no_endpoint':
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region)
    elif 's3-accelerate' in dest_endpoint_url and bucket_dest_region != 'snow':
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region)
    elif dest_endpoint_url != 'no_endpoint' and bucket_dest_region != 'snow':
        # create aws clients to see destination objects
        s3_client_dest = boto3.client('s3', 
        aws_access_key_id=access_key_dest, 
        aws_secret_access_key=secret_access_key_dest, 
        region_name=bucket_dest_region, 
        endpoint_url=dest_endpoint_url, 
        use_ssl=False, verify=False)
    else:
        # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
        session = boto3.Session(
            aws_access_key_id=access_key_dest, 
            aws_secret_access_key=secret_access_key_dest
        )

        # Connect to S3 with the specified endpoint
        if 'https' in dest_endpoint_url: # denotes new snowballs
            s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_url, verify=False)
        else:
            s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_url)

    while True:
        # get the objects in our destination bucket and volumes to compare missing objects and sync them from local to destination
        objects_in_dest = list_objects(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow'))
        local_files = get_all_local_files(volumes, include_volumes=True)

        dest_difference = {key:vol for vol, files in local_files.items() for key in files if (key not in objects_in_dest or files[key] != objects_in_dest[key])}

        # Clear the content of dest_commands.txt before writing
        with open('dest_commands.txt', 'w') as file:
            pass

        if dest_difference:
            with open('dest_commands.txt', 'w') as file:
                for obj_key, obj_vol in dest_difference.items():
                    dest_path = f"s3://{bucket_dest_name}/{bucket_dest_prefix}{obj_key}"
                    local_path = f"{obj_vol}/{obj_key}"

                    command = f"cp --concurrency 15 --destination-region {bucket_dest_region} '{local_path}' '{dest_path}'"
                    file.write(command + '\n')
            print(f"Commands have been written to dest_commands.txt.")

            # Setting up AWS environment variables to use s5cmd to move from source to local
            os.environ["AWS_ACCESS_KEY_ID"] = access_key_dest
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key_dest

            # Execute the shell dest_command
            if dest_endpoint_url == 'no_endpoint':
                dest_command = f"time ./s5cmd --stat --numworkers 64 run dest_commands.txt"
            elif dest_endpoint_url != 'no_endpoint' and bucket_dest_region != 'snow':
                dest_command = f"time ./s5cmd --stat --endpoint-url={dest_endpoint_url} --no-verify-ssl --numworkers 64 run dest_commands.txt"
            else:
                if 'https' in dest_endpoint_url: # denotes new snowballs
                    dest_command = f"time ./s5cmd --stat --endpoint-url={dest_endpoint_url} --no-verify-ssl --numworkers 64 run dest_commands.txt"
                else:
                    dest_command = f"time ./s5cmd --stat --endpoint-url={dest_endpoint_url} --numworkers 64 run dest_commands.txt"
            os.system(dest_command)
        else:
            print(f"All objects in {bucket_dest_name}/{bucket_dest_prefix} are identical in {volumes}.")

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

if __name__ == "__main__":
    main()

