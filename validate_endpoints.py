import boto3
from helper import read_config, test_endpoint
import json

def main():
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

    failed_dest_endpoints = []
    for i in range(len(dest_endpoint_urls)):
        print(f'Checking destination endpoint: {dest_endpoint_urls[i]}')
        if dest_endpoint_urls[i] == 'no_endpoint':
            s3_client_dest = boto3.client('s3', 
            aws_access_key_id=access_key_dest, 
            aws_secret_access_key=secret_access_key_dest, 
            region_name=bucket_dest_region)
        elif 's3-accelerate' in dest_endpoint_urls[i] and bucket_dest_region != 'snow':
            s3_client_dest = boto3.client('s3', 
            aws_access_key_id=access_key_dest, 
            aws_secret_access_key=secret_access_key_dest, 
            region_name=bucket_dest_region)
        elif dest_endpoint_urls[i] != 'no_endpoint' and bucket_dest_region != 'snow':
            # create aws clients to see destination objects
            s3_client_dest = boto3.client('s3', 
            aws_access_key_id=access_key_dest, 
            aws_secret_access_key=secret_access_key_dest, 
            region_name=bucket_dest_region, 
            endpoint_url=dest_endpoint_urls[i], 
            use_ssl=False, verify=False)
        else:
            # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
            session = boto3.Session(
                aws_access_key_id=access_key_dest, 
                aws_secret_access_key=secret_access_key_dest
            )

            # Connect to S3 with the specified endpoint
            if 'https' in dest_endpoint_urls[i]: # denotes new snowballs
                s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_urls[i], verify=False)
            else:
                s3_client_dest = session.resource('s3', endpoint_url=dest_endpoint_urls[i])

        if not test_endpoint(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow')):
            failed_dest_endpoints.append(dest_endpoint_urls[i])

    # set up source information
    bucket_src_name = config["source"]["bucket_name"]
    bucket_src_prefix = config["source"]["bucket_prefix"]
    bucket_src_region = config["source"]["region"]
    access_key_src = config["source"]["access_key"]
    secret_access_key_src = config["source"]["secret_access_key"]

    # set up source s3 url
    src_endpoint_urls = config["transfer_settings"]["src_endpoint_url"]

    failed_src_endpoints = []
    for i in range(len(src_endpoint_urls)):
        print(f'Checking source endpoint: {src_endpoint_urls[i]}')
        if src_endpoint_urls[i] == 'no_endpoint':
            s3_client_src = boto3.client('s3', 
            aws_access_key_id=access_key_src, 
            aws_secret_access_key=secret_access_key_src, 
            region_name=bucket_src_region)
        elif 's3-accelerate' in src_endpoint_urls[i] and bucket_src_region != 'snow':
            s3_client_src = boto3.client('s3', 
            aws_access_key_id=access_key_src, 
            aws_secret_access_key=secret_access_key_src, 
            region_name=bucket_src_region)
        elif src_endpoint_urls[i] != 'no_endpoint' and bucket_src_region != 'snow':
            # create aws clients to see destination objects
            s3_client_src = boto3.client('s3', 
            aws_access_key_id=access_key_src, 
            aws_secret_access_key=secret_access_key_src, 
            region_name=bucket_src_region, 
            endpoint_url=src_endpoint_urls[i], 
            use_ssl=False, verify=False)
        else:
            # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
            session = boto3.Session(
                aws_access_key_id=access_key_src, 
                aws_secret_access_key=secret_access_key_src
            )

            # Connect to S3 with the specified endpoint
            if 'https' in src_endpoint_urls[i]: # denotes new snowballs
                s3_client_src = session.resource('s3', endpoint_url=src_endpoint_urls[i], verify=False)
            else:
                s3_client_src = session.resource('s3', endpoint_url=src_endpoint_urls[i])

        if not test_endpoint(bucket_src_name, bucket_src_prefix, s3_client_src, isSnow=(bucket_src_region=='snow')):
            failed_src_endpoints.append(src_endpoint_urls[i])

    print(f"\nFailed dest endpoints: {failed_dest_endpoints}")
    print(f"Failed src endpoints: {failed_src_endpoints}\n")

    failed_endpoints = {
        "failed_dest_endpoints": failed_dest_endpoints,
        "failed_src_endpoints": failed_src_endpoints
    }

    # Save the dictionary to a YAML file
    with open("failed_endpoints.json", "w") as file:
        json.dump(failed_endpoints, file, indent=4)

    if failed_dest_endpoints != [] or failed_src_endpoints != []:
        print('If you are not using endpoints replace the endpoints in the config to ["no_endpoint"].\n')
        print('If you are using endpoints it is recommended to investigate the cause of the endpoint outages.')
    
    if len(failed_dest_endpoints) == len(dest_endpoint_urls):
        print('\nSERIOUS ERROR. ALL DESTINATION ENDPOINTS HAVE FAILED. WILL NOT RUN. CHECK ENDPOINTS AND CONNECTION.\n')
    elif len(failed_src_endpoints) == len(src_endpoint_urls):
        print('\nSERIOUS ERROR. ALL SOURCE ENDPOINTS HAVE FAILED. WILL NOT RUN. CHECK ENDPOINTS AND CONNECTION.\n')
    elif len(failed_dest_endpoints) == 0 and len(failed_src_endpoints) == 0:
        print('\nSUCCESS. All endpoints are working.')
    else:
        print('\nWARNING. Some endpoints failed, however the data transfer might still work.\n')

if __name__ == "__main__":
    main()

