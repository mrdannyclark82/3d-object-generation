#
# SPDX-FileCopyrightText: Copyright (c) 1993-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import subprocess
import os
import sys

def set_environment_variable():
    """
    Set the CHAT_TO_3D_PATH environment variable to the current directory
    using the setx command on Windows.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the current directory path
        current_path = os.getcwd()
        
        # The environment variable name
        env_var_name = "CHAT_TO_3D_PATH"
        
        # Construct the setx command
        # setx command format: setx VARIABLE_NAME "VALUE"
        command = ['setx', env_var_name, current_path]
        
        print(f"Setting {env_var_name} to: {current_path}")
        
        # Execute the setx command
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            print(f"SUCCESS: {env_var_name} environment variable set")
            print(f"Path: {current_path}")
            return True
        else:
            print(f"ERROR: Failed to set environment variable")
            if result.stderr:
                print(f"Error details: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception occurred: {str(e)}")
        return False

def verify_environment_variable():
    """
    Verify that the environment variable was set correctly.
    Note: This will only work in new processes after the variable is set.
    
    Returns:
        bool: True if found, False otherwise
    """
    try:
        # Try to get the environment variable
        env_value = os.environ.get("CHAT_TO_3D_PATH")
        
        if env_value:
            print(f"VERIFY: Environment variable found: {env_value}")
            return True
        else:
            print("VERIFY: Environment variable not found in current process (normal for setx)")
            return False
            
    except Exception as e:
        print(f"ERROR: Verification failed: {str(e)}")
        return False

def main():
    """
    Main function to set the environment variable.
    Returns appropriate exit code for batch file integration.
    """
    print("Setting CHAT_TO_3D_PATH environment variable...")
    
    # Set the environment variable
    success = set_environment_variable()
    
    if success:
        print("Environment variable set successfully.")
        print("Note: Variable will be available in new command prompt windows.")
        
        # Optional verification (will likely show as not found in current process)
        verify_environment_variable()
        
        return 0  # Success exit code
    else:
        print("Failed to set environment variable.")
        return 1  # Error exit code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
