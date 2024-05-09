import subprocess
import os
import concurrent.futures

def main():
    # Ask the user if the volumes have been provisioned and setup_volumes.py has been run
    volumes_ready = input("\nHave the volumes been provisioned and setup_volumes.py run (y/n)? ")
    # Proceed only if the answer is 'y'
    if volumes_ready.lower() == 'y':
        pass
    else:
        print("Please ensure that volumes are provisioned and setup_volumes.py is run before proceeding.")
        quit()

    # Ask the user if the config.yaml has been verified to be correct
    config_verified = input("\nHas the config.yaml been verified to be correct (y/n)? ")
    # Proceed only if the answer is 'y'
    if config_verified.lower() == 'y':
        # Run validate_endpoints.py and print its output in real time
        try:
            os.system('python validate_endpoints.py')
        except Exception as e:
            print("Failed to run validate_endpoints.py")
            print("Error:", e)
            quit()
    else:
        print("Please verify the config.yaml before proceeding.")
        quit()

    endpoints_verified = input("\nAre the endpoints valid or acceptable (y/n)? ")
    # Proceed only if the answer is 'y'
    if endpoints_verified.lower() == 'y':
        # Run src_connect_test.py and print its output in real time
        try:
            os.system('python src_connect_test.py')
        except Exception as e:
            print("Failed to run src_connect_test.py")
            print("Error:", e)
            quit()
    else:
        print("Please verify the config.yaml and your endpoints before proceeding.")
        quit()

    src_connect_verified = input("\nis this the expected source output (y/n)? ")
    # Proceed only if the answer is 'y'
    if src_connect_verified.lower() == 'y':
        # Run dest_connect_test.py and print its output in real time
        try:
            os.system('python dest_connect_test.py')
        except Exception as e:
            print("Failed to run dest_connect_test.py")
            print("Error:", e)
            quit()
    else:
        print("Please verify the config.yaml")
        quit()
    
    dest_connect_verified = input("\nis this the expected destination output (y/n)? ")
    # Proceed only if the answer is 'y'
    if dest_connect_verified.lower() == 'y':
        # Run reset.py and print its output in real time
        try:
            os.system('python reset.py')
        except Exception as e:
            print("Failed to run reset.py")
            print("Error:", e)
            quit()

        # Run repair_ledger.py and print its output in real time
        try:
            os.system('python repair_ledger.py')
        except Exception as e:
            print("Failed to run repair_ledger.py")
            print("Error:", e)
            quit()
    else:
        print("Please verify the config.yaml")
        quit()

    def run_script(script_name):
        """Function to run a python script using subprocess."""
        print(f"Running {script_name}...")
        # Run the script and capture the output
        result = subprocess.run(['python', script_name], capture_output=True, text=True)
        # Output the results
        print(f"Output of {script_name}:")
        print(result.stdout)
        # print("Errors if any:")
        # print(result.stderr)

    final_approval = input("\nDo you want to begin the data transfer (y/n)? ")
    # Proceed only if the answer is 'y'
    if final_approval.lower() == 'y':
        print('Executing src_sync_mvol.py and dest_sync_mvol.py.')
        # Scripts to run concurrently
        scripts = ["src_sync_mvol.py", "dest_sync_mvol.py"]

        # Using ThreadPoolExecutor to run scripts concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Map the run_script function to the scripts
            executor.map(run_script, scripts)

        print('\n\nALL DATA IS MOVED. RUN repair_ledger.py TO DO A FINAL DATA INTEGRITY CHECK.')
    else:
        print("Please verify the config.yaml and your endpoints before proceeding.")
        quit()

    
    
if __name__ == "__main__":
    main()
