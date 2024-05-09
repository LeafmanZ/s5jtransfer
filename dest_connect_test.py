import boto3
from helper import read_config, list_objects
import json

def main():
    # Read data from JSON file
    with open('failed_endpoints.json', 'r') as file:
        data = json.load(file)

    # Extract values
    failed_dest_endpoints = data["failed_dest_endpoints"]

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
    
    objects_in_dest = list_objects(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow'))
    print(objects_in_dest)

    print(f'\n\nDestination: S3://{bucket_dest_name}/{bucket_dest_prefix}')
    print(f'Total Number of Objects: {len(objects_in_dest)}')
    print(f'Total Size of Objects (bytes): {sum(int(obj) for obj in objects_in_dest.values())}')

if __name__ == "__main__":
    main()
