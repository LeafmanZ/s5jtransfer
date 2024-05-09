import boto3
import pandas as pd
from helper import read_config, list_objects
import json

def main():
    # Read data from JSON file
    with open('failed_endpoints.json', 'r') as file:
        data = json.load(file)

    # Extract values
    failed_dest_endpoints = data["failed_dest_endpoints"]
    failed_src_endpoints = data["failed_src_endpoints"]

    config = read_config()
    
    if not config:
        print("Failed to read the configuration.")
        return

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

    # get the objects in our destination bucket and source buckets to compare missing objects
    objects_in_src = list_objects(bucket_src_name, bucket_src_prefix, s3_client_src, isSnow=(bucket_src_region=='snow'))
    objects_in_dest = list_objects(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow'))

    dest_moved = {key: objects_in_src[key] for key in objects_in_src if (key in objects_in_dest and objects_in_src[key] == objects_in_dest[key])}
    dest_not_moved = {key: objects_in_src[key] for key in objects_in_src if (key not in objects_in_dest or objects_in_src[key] != objects_in_dest[key])}
    
    num_objects_missing = len(objects_in_src) - len(dest_moved)
    if num_objects_missing == 0:
        print('All objects have been successfully moved from source to destination.')
        complete_status = {"Status": "Completed"}
    elif num_objects_missing <= 10:
        print('A few objects were missing, ledger has been updated.')
        print('Number of objects missing:', num_objects_missing)
        src_ledger_df = pd.DataFrame(list(dest_moved.items()), columns=['Key', 'Size'])
        src_ledger_df.to_csv('src_ledger.csv', index=False)
        print('Please run src_sync_mvol.py and dest_sync_mvol.py again.')
        file_path = "missing.txt"
        # Open the file in write mode
        with open(file_path, "w") as file:
            # Write each key-value pair in the dictionary to the file
            for key, value in dest_not_moved.items():
                file.write(f"{key}: {value}\n")
        print('Saved missing objects to missing.txt')

        print('Missing Objects:')
        for key, value in dest_not_moved.items():
            print(f"{key}: {value}")

        complete_status = {"Status": "Semi-Incomplete"}
    else:
        print('Objects were missing, ledger has been updated.')
        print('Number of objects missing:', num_objects_missing)
        src_ledger_df = pd.DataFrame(list(dest_moved.items()), columns=['Key', 'Size'])
        src_ledger_df.to_csv('src_ledger.csv', index=False)
        print('Please run src_sync_mvol.py and dest_sync_mvol.py again.')
        complete_status = {"Status": "Incomplete"}

    # Update sync_progress.json
    with open('sync_progress.json', 'w') as json_file:
        json.dump(complete_status, json_file)

if __name__ == "__main__":
    main()
