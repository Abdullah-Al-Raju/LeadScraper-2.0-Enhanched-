"""
Terminal Capture System - Python Version
Captures output AND shows it in real-time (no freezing!)
Works on ANY platform (Windows, Mac, Linux)
"""

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

# Configuration
CAPTURE_FILE = Path("logs/terminal_capture.txt")
MAX_CAPTURES = 5

# Ensure logs directory exists
CAPTURE_FILE.parent.mkdir(exist_ok=True)

def capture_command(command_args):
    """Execute command, show output in real-time, AND capture it"""
    
    command_string = ' '.join(command_args)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Header
    header = f"""
{'='*80}
CAPTURE: {timestamp}
COMMAND: {command_string}
{'='*80}

"""
    
    print(header)
    
    # Capture buffers
    stdout_lines = []
    stderr_lines = []
    
    try:
        # Use Popen for real-time output streaming
        process = subprocess.Popen(
            command_string,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered
            encoding='utf-8',
            errors='replace'
        )
        
        # Stream stderr in a separate thread (so stdout doesn't block)
        def stream_stderr():
            for line in process.stderr:
                stderr_lines.append(line)
                print(line, end='', file=sys.stderr)
        
        stderr_thread = threading.Thread(target=stream_stderr, daemon=True)
        stderr_thread.start()
        
        # Stream stdout in main thread
        for line in process.stdout:
            stdout_lines.append(line)
            print(line, end='')
        
        # Wait for process and stderr thread to finish
        process.wait()
        stderr_thread.join(timeout=5)
        
        stdout_text = ''.join(stdout_lines)
        stderr_text = ''.join(stderr_lines)
        
        output = f"STDOUT:\n{stdout_text}\n\nSTDERR:\n{stderr_text}\n\nEXIT CODE: {process.returncode}"
        exit_code = process.returncode
            
    except Exception as e:
        output = f"ERROR: {str(e)}"
        print(output, file=sys.stderr)
        exit_code = 1
    
    # Create capture block
    capture_block = header + f"OUTPUT:\n{output}\n\nEND OF CAPTURE\n{'='*80}\n\n"
    
    # Load existing captures
    if CAPTURE_FILE.exists():
        existing = CAPTURE_FILE.read_text(encoding='utf-8')
    else:
        existing = ""
    
    # Add new capture to top
    all_captures = capture_block + existing
    
    # Keep only last 5
    captures = all_captures.split("END OF CAPTURE")
    if len(captures) > MAX_CAPTURES:
        captures = captures[:MAX_CAPTURES]
        all_captures = "END OF CAPTURE".join(captures)
    
    # Save
    CAPTURE_FILE.write_text(all_captures, encoding='utf-8')
    
    print(f"\n[CAPTURED] Output saved to: {CAPTURE_FILE}")
    
    return exit_code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cap.py <command>")
        print('Example: python cap.py python main.py --discover "Dhaka" --quantity 5')
        sys.exit(1)
    
    exit_code = capture_command(sys.argv[1:])
    sys.exit(exit_code)
