## Overview
s5jtransfer_v12 is a custom data transfer tool tailored for use on Linux operating systems with AMD64 architecture. It's developed using Go and Python, integrating with the s5cmd tool for efficient interaction with Amazon S3 services. This tool is specifically designed to address the limitations found in standard s5cmd operations, particularly in its sync capabilities.

## Key Features
- **Enhanced Sync Capabilities**: Unlike standard s5cmd, s5jtransfer_v12 supports robust dual sync operations with checksum verification. This is crucial for maintaining data integrity across complex tasks.
- **Multiple Volume Support**: Improves read/write speeds by facilitating data transfer across multiple storage volumes.
- **Simultaneous Endpoint Connections**: Allows multiple connections to various endpoints simultaneously, optimizing the data transfer process and avoiding bottlenecks.
- **Detailed Ledger System**: Keeps a comprehensive log of data at every stage of the transfer, ensuring traceability and accountability.
- **Versa SD-WAN Compatibility**: Unlike the native s5cmd, s5jtransfer_v12 can transfer data via Versa SD-WAN networks, expanding its usability in more complex network environments.

## Motivation
The development of s5jtransfer_v12 was motivated by the need for a more reliable and efficient data handling tool, especially evident during incidents like the power outage at a forward edge location. During this event, standard s5cmd sync operations failed, leading to significant data transfer issues. The s5jtransfer_v12 script successfully addressed these challenges, proving its efficacy over conventional tools.

---

## Quick Start
Here’s a quick start guide for using s5jtransfer_v12:

1. Prepare your compute device (use Snowball Compute EC2 or any standard computer).
2. Attach as many volumes as possible to your device.
3. Install necessary dependencies as listed in the Dependency Setup instructions.
4. Navigate to the directory `/<your_path>/s5jtransfer/`.
5. For first-time setup, execute `python setup_volumes.py`.
6. Update `config.yaml` with correct source and destination details, including S3 bucket paths, access keys, and endpoints.
7. Start the data transfer by running `python data_transfer.py`.
8. The program will guide you through the process to ensure your data is correctly synced from the source to the destination bucket.

---

## Setup and Requirements
s5jtransfer_v12 requires a Linux operating system on AMD64 architecture. It is built with Go and Python, requiring these environments to be pre-installed. Users must also have access to Amazon S3 services and, if utilizing its full capabilities, a Versa SD-WAN setup.

This tool is ideal for users needing a reliable, high-performance data transfer solution capable of handling complex, high-volume data syncing tasks with enhanced security and monitoring.

Here's a cleaned-up version of the README for setting up the requirements and dependencies:

- **Operating System**: Linux/amd64 (Ubuntu 22.04 recommended)
- **Go**: version 1.21.5
- **s5cmd**: version 2.2.2
- **Python**: version >= 3.11.0

## Dependency Setup Instructions

### Setup from AMI

If using the AMI `s5jtransfer_v12`, skip the rest of this section as all configurations are pre-set.

### Setup from Scratch

#### 1. Prepare Environment
Navigate to the appropriate folder:
```
cd path/to/this/s5jtransfer
```
Ensure that you are in the correct directory.

#### Prerequisites
- Linux must be installed (Ubuntu 22.04 recommended)

#### 2. Installing Go

If `go1.21.1.linux-amd64.tar.gz` is not present and you have internet access:
```
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
```
Install Go by executing:
```
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo "export PATH=\$PATH:/usr/local/go/bin" >> ~/.profile
source ~/.profile
go version
```
You should see:
```
go version go1.21.5 linux/amd64
```

#### 3. Installing s5cmd

If `s5cmd_2.2.2_Linux-64bit.tar.gz` is not present and you have internet access:
```
wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
```
Install s5cmd by executing:
```
tar -xzf s5cmd_2.2.2_Linux-64bit.tar.gz
chmod +x s5cmd
./s5cmd
```
Output will show s5cmd commands and usage guidelines.

#### 4. Installing Python with Anaconda

To install Python using Anaconda:
```
wget https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Linux-x86_64.sh
bash Anaconda3-2024.02-1-Linux-x86_64.sh
```
Follow the on-screen instructions. After installation, configure environment:
```
nano ~/.bashrc
```
Add the following line at the end:
```
source /home/ubuntu/anaconda3/bin/activate
```
Save and exit:
- `Ctrl+O`, `Enter`, `Ctrl+X`
```
sudo reboot
```
Verify installation:
```
conda
```
You should see conda help information.

Install additional packages:
```
conda install pip
pip install boto3
pip install pandas
```
---

### Usage Instructions

#### Setup and Initial Configuration

1. **Change to the Project Directory:**
   ```bash
   cd path/to/this/s5jtransfer
   ```

   Verify that you are in the correct directory before proceeding.

2. **Using the Primary Script:**
   
   It is recommended to use `data_transfer.py` for simplicity. For a more detailed control of the synchronization process, individual Python scripts can be used as described below.

#### Part 1: Reset Environment

   **Initial Setup or Complete Reset:**
   - Use this step for the initial setup or when a complete reset is needed.
   - Clear previous run data and set up the environment afresh.
   
   **Commands to Execute:**
   ```bash
   python reset.py
   python setup_volumes.py  # Optional: Only run this if you need to manage multiple storage volumes.
   ```

#### Part 2: Configure `config.yaml`

   **Editing Configuration:**
   - Changes in this file require re-execution of Part 3.
   - Use `nano` to edit the configuration:
     ```bash
     nano config.yaml
     ```
   - Fill out the parameters within double quotes `""` as described below:

     **Source Configuration:**
     - **Source Bucket Name:** Name of the source S3 bucket.
     - **Source Bucket Prefix:** Path within the source bucket (omit leading '/', include trailing '/').
     - **Source Region:** Region where the source bucket is located (e.g., "us-east-1").
     - **Source Access Key and Secret:** Credentials with S3 permissions for the source.

     **Local Configuration:**
     - **Intermediary Directory:** Temporary storage during transfers, crucial for single volume setups.

     **Destination Configuration:**
     - Similar structure as source configuration but for the destination S3 bucket.
   
     **Transfer Settings:**
     - Specify max file sizes for transfers and endpoint URLs for source and destination buckets.

#### Part 3: Begin Data Transfer

   **Execution and Monitoring:**
   - Scripts can be stopped using `Ctrl+C`.
   - Subsequent runs don’t require redoing Part 1 or 2 unless changes were made.
   - Observe transfer logs for source and destination activity.
   - Run the following for concurrent data synchronization:
     ```bash
     python src_sync_mvol.py
     python dest_sync_mvol.py
     ```
   - The system ensures efficient data management and prevents redundancy using a ledger system.

These steps should guide you through setting up and managing your data transfers effectively. Ensure that any command modifications (e.g., using `python` for Anaconda environments) are adjusted as per your setup requirements.

---

### Development Structure Overview

#### Supporting Python Scripts

- **reset.py**: This script is used for deleting contents within specified directories and performing cleanup based on a configuration file. It employs `os` for directory and file operations and `shutil` for removing directory trees. Configuration is read using a custom `read_config` function from a helper module.

- **setup_volumes.py**: Automates the partitioning, formatting, and mounting of block devices on Linux and sets directory permissions. It executes shell commands using `subprocess`, parses command outputs with `json`, and handles filesystem operations via `os`.

- **helper.py**: A utility module that facilitates interactions with the local filesystem and AWS S3 buckets. Functions include reading YAML configuration files, listing S3 bucket objects, filtering local files by name, obtaining disk usage, and aggregating files across multiple volumes. It utilizes `yaml`, `os`, `boto3`, `subprocess`, and `re` libraries.

- **repair_ledger.py**: Compares objects between source and destination S3 buckets, identifying discrepancies. It updates `src_ledger.csv` to ensure accurate synchronization of missing objects with `src_sync_mvol.py`.

- **validate_endpoints.py**: Checks the reachability of specified endpoints and verifies their configuration and operational status. Results, including any issues, are saved in `failed_endpoints.json`. The script advises on the feasibility of data transfers based on the health of these endpoints.

- **src_connect_test.py** and **dest_connect_test.py**: These scripts test the connectivity to the respective source and destination S3 buckets by listing all objects after configuring credentials in `config.yaml`.

#### Core Python Scripts

- **src_sync_mvol.py**: Synchronizes data from an Amazon S3 bucket to local storage volumes. It manages S3 connections, local storage space, and file discrepancies. Utilizes `s5cmd` for file transfers and maintains a ledger for tracking progress.

- **dest_sync_mvol.py**: Transfers files from local storage to an Amazon S3 bucket. It checks for new or differing files to transfer and deletes them locally post-transfer to avoid duplication.

- **data_transfer.py**: Orchestrates the simultaneous execution of `src_sync_mvol.py` and `dest_sync_mvol.py`, running them continuously as needed. This script ensures that file synchronization is maintained between local and S3 storage.

- **Configuration Adjustments**: When altering volume storage paths, comment out the default path settings in the respective sync scripts and specify the new paths as needed.

#### File Transfer Program

- **s5cmd**: A robust tool for executing file operations on S3 and local filesystems. It supports a wide range of commands, tab completion, and wildcard utilization, enhancing the efficiency of file management tasks. While `s5cmd` is commonly used in our scripts, `src_sync_mvol.py` utilizes the native S3 CLI for specific scenarios involving Snowball devices.