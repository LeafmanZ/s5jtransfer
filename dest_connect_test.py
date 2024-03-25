import boto3
from helper import read_config, list_objects

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
    

    objects_in_dest = list_objects(bucket_dest_name, bucket_dest_prefix, s3_client_dest, isSnow=(bucket_dest_region=='snow'))
    print(objects_in_dest)
    print(f'\n\nTotal Number of Objects: {len(objects_in_dest)}')
    print(f'\n\nTotal Size of Objects (bytes): {sum(int(obj) for obj in objects_in_dest.values())}')

if __name__ == "__main__":
    main()
