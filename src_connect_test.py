import boto3
from helper import read_config, list_objects
import json

def main():
    # Read data from JSON file
    with open('failed_endpoints.json', 'r') as file:
        data = json.load(file)

    # Extract values
    failed_src_endpoints = data["failed_src_endpoints"]

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

    # I think we need to accept a list and split on ','
    # for the sync we will need to cycle endpoints when writing commands
    # we dont need to cycle endpoints to generate multiple clients since a single client can see into the the entire 

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

    objects_in_src = list_objects(bucket_src_name, bucket_src_prefix, s3_client_src, isSnow=(bucket_src_region=='snow'))
    print(objects_in_src)

    print(f'\n\nSource: S3://{bucket_src_name}/{bucket_src_prefix}')
    print(f'Total Number of Objects: {len(objects_in_src)}')
    print(f'Total Size of Objects (bytes): {sum(int(obj) for obj in objects_in_src.values())}')


if __name__ == "__main__":
    main()