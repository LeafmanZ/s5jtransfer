About s5jtransfer_v11:

The text describes a set of requirements and setup instructions for a data transfer application or script, specifically tailored for the Linux operating system on AMD64 architecture. 
The application is developed in Go and Python, and it utilizes a tool called s5cmd for interacting with Amazon S3 services.

The preference for custom s5jtransfer_v11 scripts over the standard s5cmd stems from the latter's limitations, particularly in robust sync features. 
While standard s5cmd excels in creating concurrent copy commands for efficient data transfer, it falls short in preventing redundant data transfer. 
This issue becomes evident in complex tasks, such as performing a dual sync from an S3 Snowball to local storage and then to another S3 bucket.
Such a limitation was highlighted during a power outage at the forward edge, where the native s5cmd sync failed to transfer data from the archiver to the snowball, 
a problem that was resolved using the custom s5jtransfer_v11 sync script.

The custom s5jtransfer_v11 scripts offer enhanced capabilities, including dual sync with checksum verification, support for multiple volume transfers to improve read/write speeds, and avoidance of data transfer bottlenecks. 
Additionally, they maintain a detailed ledger to monitor data at every transfer stage. 
A key advantage of these s5jtransfer_v11 scripts is their compatibility with Versa SD-WAN, enabling data transfer via this network, a functionality absent in the native s5cmd.

=====================================================================================================================================================================================

TLDR I hate reading, I just want to start using s5jtransfer_v11:

1. Attach as many volumes as possible to your EC2 instance for optimal performance.
2. Edit the `config.yaml` file by entering `nano config.yaml`. Save your changes with `Ctrl+O` and exit with `Ctrl+X`.
3. Execute the script `setup_volumes.py`.
4. If starting from the beginning, run `python reset.py`.
5. Test your connection to the destination bucket and verify it's the correct one by running `python dest_connect_test.py`.
6. Ensure you can connect to the source bucket and it's the correct one by executing `python src_connect_test.py`.
7. Start the destination sync process in the background by running `nohup python dest_sync_mvol.py > /dev/null 2>&1 &`.
8. Similarly, start the source sync process in the background with `nohup python src_sync_mvol.py > /dev/null 2>&1 &`.
9. Confirm both sync processes are running by checking active Python processes with `ps aux | grep python`.
10. Monitor the progress of moved objects with `wc -l src_ledger.csv`.
11. Completion is indicated when `src_ledger.csv` matches the count from `src_connect_test.py` plus one.
12. Perform a final verification with `python repair_ledger.py` to ensure all objects were correctly moved.
13. If the count in `src_ledger.csv` decreases, indicating objects were removed, first identify all related process IDs with `ps aux | grep python`. Terminate these processes with `kill <PID>` for both `dest_sync_mvol.py` and `src_sync_mvol.py`.
14. Repeat steps 7 to 13 until nothing is removed by `python repair_ledger.py`.

=====================================================================================================================================================================================

Requirements:

    linux/amd64 (AMI is built on Ubuntu 22.04)
    go version = 1.21.5
    s5cmd version = 2.2.2
    python version >= 3.11.0

=====================================================================================================================================================================================

Set up instructions (Applicable if prerequisites aren't installed):

    SETUP FROM AMI

    And then skip the rest of this section because everything is already set up and configured in the s5jtransfer_v11 ami.

    SETUP FROM SCRATCH

    Navigate to this folder:
    cd path/to/this/s5jtransfer
    Ensure that you are in the correct directory.

    Prerequisites:
        - Linux must be installed (Ubuntu 22.04 recommended)

    Part 1: Installing GOlang

        If the file `go1.21.1.linux-amd64.tar.gz` is not present and internet access is available,
        you can obtain the file by executing the following command:
            wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz

        Execute the following commands in sequence:
            sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
            echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.profile
            source ~/.profile
            go version

        Upon successful execution, you should receive an output similar to:
            go version go1.21.5 linux/amd64

    Part 2: Installing s5cmd

        If the file `s5cmd_2.2.2_Linux-64bit.tar.gz` is not present and internet access is available,
        you can obtain the file by executing the following command:
            wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz

        Execute the following commands in sequence:
            tar -xzf s5cmd_2.2.2_Linux-64bit.tar.gz
            chmod +x s5cmd
            ./s5cmd

        After executing, you'll observe an output displaying various s5cmd commands along with their usage guidelines.
        
    Part 3: Installing Python with Anaconda

        To install the latest version of Python, follow these steps:
            Navigate to:
                https://www.anaconda.com/download
            Copy the download link. It should look like:
                https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Linux-x86_64.sh
            In terminal execute:
                wget https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Linux-x86_64.sh
            In terminal execute:
                bash Anaconda3-2024.02-1-Linux-x86_64.sh
            
        Follow the on-screen instructions during the installation process, pressing 'enter' and agreeing ('yes') when prompted.
        
        In terminal exectute:
            nano ~/.bashrc
        At the very bottom of the file add the following line:
            source /home/ubuntu/anaconda3/bin/activate
        Then press the keys to save and close the file:
            Ctrl+O
            Ctrl+X
        In terminal exectute:
            sudo reboot

        To verify that anaconda has been installed successfully, in terminal execute:
            conda
            
        After executing, you should see the conda help information displayed.

=====================================================================================================================================================================================

Usage:

    Navigate to this folder:
    cd path/to/this/s5jtransfer
    Ensure that you are in the correct directory.

    Part 1: Reset environment
        
        Execute this command solely on the initial run or when a complete reset is necessary, resulting in a re-transfer of all data.
    
        We need to refresh the environment by removing previous run data and details. 
        Subsequently, establish our volumes if distributing data across multiple concurrent volumes.
        
        Execute the following commands in sequence (if you are using anaconda use python instead of python):
            python reset.py
            python setup_volumes.py # only use setup_volumes.py if you need to provision volumes and attach them to a folder.
    
    Part 2: Configure config.yaml
        
        Should any modifications be made in this section, it will be essential to re-execute Part 3.

        Execute the following command:
            nano config.yaml
        
        You will have to fill out the following parameters inside this configuration file where there are double quotes ""

        Source Configuration:
            Source Bucket Name: Specify the name of the originating bucket where your data is stored.
            Source Bucket Prefix: Indicate the subdirectory within your source bucket. Omit the preceding '/', but ensure to include a trailing '/'.
            Source Region: Denote the geographic location of your bucket, for example, "us-east-1". For buckets located in a snowball, use "snow" as the region.
            Source Access Key: Provide the access key associated with a user who has S3 permissions for the source S3 bucket.
            Source Secret Access Key: Supply the secret access key corresponding to the user with S3 permissions for the source S3 bucket.
            
        Local Configuration:
            Intermediary Directory: This directory acts as a temporary storage area during data transfer. Its configuration is crucial if utilizing a single volume compute.
        
        Destination Configuration:
            Destination Bucket Name: Enter the name of the bucket where you intend your data to be transferred.
            Destination Bucket Prefix: Specify the subdirectory within your destination bucket. Do not include a preceding '/', but ensure a trailing '/' is added.
            Destination Region: Indicate the geographic location of your destination bucket, such as "us-east-1". Note that snowball is not supported as a destination.
            Destination Access Key: Provide the access key for a user with S3 permissions to the destination S3 bucket.
            Destination Secret Access Key: Supply the secret access key for the user with S3 permissions to the destination S3 bucket.
        
        Transfer Settings:
            Max Transfer Size (Source to Local): Define the maximum file size (in bytes) allowed for a single transfer from the source to the local storage.
            Max Transfer Size (Local to Destination): [Not Implemented] State the maximum total file size (in gigabytes) permitted for a single transfer from the local storage to the destination.
            Destination Endpoint URL: Enter the endpoint URL for the destination S3 bucket. If not applicable, set as 'no_endpoint'.
            Source Endpoint URL: Provide the endpoint URL for the source S3 bucket. If not applicable, set as 'no_endpoint'. For legacy snowball, use 'http' and the port number, whereas for others, use 'https' without specifying the port number.

    Part 3: Begin transfer
        
        To terminate the scripts, use Ctrl+C.
        Restarting the scripts doesn't require repeating Part 1 or Part 2, unless previously specified in the earlier sections.

        In both scripts, you'll notice messages indicating the source and destination of data transfers. 
        When there's no data to transfer, the scripts will simply report that they're scanning for new data to move.

        For transfers conducted on a machine equipped with a multiple volume setup:
            Whenever possible, we utilize multiple volumes because each volume has restricted read/write capabilities. 
            By writing to several volumes simultaneously, we can achieve higher data transfer rates.

            Utilize the src_sync_mvol.py script to continuously transfer data from your source S3 bucket to your multiple volume directories.
            Concurrently, the dest_sync_mvol.py script will be responsible for persistently transferring data from all of the multiple volume directories to the destination S3 bucket.
            To execute these concurrently, we will utilize sync_mvol.py.
            Inherent logic, integrated with a ledger system, guarantees that data once transferred will not be redundantly moved.
            Additionally, the management of storage space from the source to the multiple volume directories is seamlessly handled and completed automatically.

            Execute the following command (if you are using anaconda use python instead of python):
                python sync_mvol.py

        In both scripts, you'll notice messages indicating the source and destination of data transfers. 
        When there's no data to transfer, the scripts will simply report that they're scanning for new data to move.

=====================================================================================================================================================================================

Development Structure:

    Supporting python scripts:

        reset.py
            The script provides functionality to delete contents within specified directories and perform cleanup based on a configuration file. 
            It utilizes os for directory and file operations, shutil for removing directory trees, and a custom read_config function from a helper module.

        setup_volumes.py
            Python script automates partitioning, formatting, and mounting of block devices on Linux, also setting directory permissions. 
            It executes shell commands using subprocess, parses command output with json, and performs filesystem operations via os.

        helper.py
            Python module for interacting with local filesystem and AWS S3 buckets. It includes functions to read a YAML configuration file, 
            list objects in an S3 bucket (with support for S3 on Outposts), list local files excluding those ending with numbers, get disk usage details for a directory, 
            and aggregate local files across multiple volumes. The script employs libraries like yaml for configuration parsing, os for filesystem operations, 
            boto3 for AWS S3 interactions, subprocess for executing shell commands, and re for regular expressions.

        src_connect_test.py
            Python script to test connectivity to source s3 bucket.
            After putting the in the proper credentials necessary for an s3 bucket for cloud or snowball in config.yaml run the script to see if it correctly lists all the objects inside the bucket.

        dest_connect_test.py
            Python script to test connectivity to destination s3 bucket.
            After putting the in the proper credentials necessary for an s3 bucket for cloud or snowball in config.yaml run the script to see if it correctly lists all the objects inside the bucket.

    Core python scripts:

        All scripts inherit functionality from helper.py to parse configurations, manage AWS S3 interactions, and managing filesystem operations.

        [src_sync_mvol.py]

            This Python script is designed to synchronize data from an Amazon S3 bucket to local storage volumes. 
            It reads configuration settings, establishes a connection to the S3 bucket using the Boto3 library, and calculates available space on local volumes. 
            The script then identifies files that are either missing or have a size discrepancy in the local storage compared to the S3 bucket, 
            generates a list of transfer commands, and executes them using the s5cmd tool. 
            Additionally, it maintains a ledger file to track the synchronization progress and performs a pseudo checksum to verify successful transfers, 
            removing any discrepancies from the ledger. The process repeats in a loop, checking for new data in the source bucket.

        [dest_sync_mvol.py]

            This Python script facilitates the transfer of files from local storage volumes to an Amazon S3 bucket. 
            Initially, it reads configuration details and establishes a connection to the S3 bucket using the Boto3 library. 
            The script then identifies files in local storage that are either missing or have size differences in the S3 bucket, generates commands to transfer these files, 
            and executes them using the s5cmd tool. After the transfer, it attempts to delete the successfully transferred files from the local storage to prevent duplication. 
            The process repeats in a loop, consistently checking for new files to transfer.

        [sync_mvol.py]

            The provided Python code uses the subprocess module to simultaneously execute two scripts, 'src_sync_mvol.py' and 'dest_sync_mvol.py',
            and executes them perpetually until canceled.

        If multi volumes [src_sync_mvol.py, dest_sync_mvol.py] have already been provisioned to a different folder naming convention (formatted and attached to a folder) make the following edits to the code in the script that you are using:
            Find the following lines in the script and comment them out with a preceeding #:
                base_path = "/tmp/volume-"
                volumes = [base_path + str(i).zfill(2) for i in range(1, 100) if os.path.exists(base_path + str(i).zfill(2))]
            Add the following line with your folders you want to transfer data to or from locally.
                volumes = ['/mnt/path/to/your/volume', '/usr/another/path/to/folder', '/local/example']

    File transfer program:

        s5cmd
            s5cmd is a very fast S3 and local filesystem execution tool. It comes with support for a multitude of operations including tab completion and wildcard support for files, 
            which can be very handy for your object storage workflow while working with large number of files.

            All of the core python scripts invoke s5cmd to make file transfers except for src_sync_mvol.py when moving data from snowball s3, where it will use native s3 cli.