import subprocess
import os
import sys

def run_bdd():
    # Define paths
    base_dir = r"d:\Tesis\ADN4RESEARCH"
    output_file = os.path.join(base_dir, "evidencias_cap3", "A_BDD", "behave_output.txt")
    features_path = os.path.join(base_dir, "tests", "acquisition", "features")
    
    print(f"Running BDD tests from {features_path}...")
    print(f"Output will be saved to {output_file}")

    # Command to run behave
    # Using 'poetry run behave'
    cmd = ["poetry", "run", "behave", features_path, "--no-color"]
    
    try:
        # Run behave and capture output
        print(f"Running BDD tests (behave) in {base_dir}...")
        with open(output_file, "w", encoding="utf-8") as f:
            # We use subprocess to capture stdout/stderr properly
            # We use subprocess.Popen to capture stdout/stderr properly and stream it
            process = subprocess.Popen(
                cmd,
                cwd=base_dir,
                stdout=subprocess.PIPE, # Capture stdout
                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                text=False, # Read as bytes, then decode
                encoding=None, # No automatic decoding by Popen
                env=os.environ.copy() # Pass current env vars
            )
            
            # Read line by line to write to file
            # Use distinct decoding to avoid crash
            for line_bytes in process.stdout:
                line_str = line_bytes.decode('utf-8', errors='replace')
                f.write(line_str)
                # print(line_str, end='') # Optional: print to console
        
        process.wait()
        
        if process.returncode == 0:
            print("[OK] BDD Tests Completed Successfully.")
        else:
            print(f"[FAIL] BDD Tests Failed with return code {process.returncode}. Check output file.")

    except Exception as e:
        print(f"[ERROR] Error running BDD tests: {e}")

if __name__ == "__main__":
    run_bdd()
