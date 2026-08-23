"""
Terminal Capture System - Python Version
Captures output AND shows it in real-time (no freezing!)
Works on ANY platform (Windows, Mac, Linux)
"""

import subprocess
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# Configuration
CAPTURE_FILE = Path("logs/terminal_capture.txt")
MAX_CAPTURES = 5

# Ensure logs directory exists
CAPTURE_FILE.parent.mkdir(exist_ok=True)

def _generate_header(command_string: str) -> str:
    """Generate the capture block header."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
{'='*80}
CAPTURE: {timestamp}
COMMAND: {command_string}
{'='*80}

"""

def _execute_and_stream(command_string: str) -> Tuple[str, int]:
    """Execute command, stream output in real-time, and return (output, exit_code)."""
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

    return output, exit_code

def _save_capture(header: str, output: str) -> None:
    """Save the capture to file, keeping only the last MAX_CAPTURES."""
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

def capture_command(command_args: List[str]) -> int:
    """Execute command, show output in real-time, AND capture it"""
    command_string = ' '.join(command_args)

    header = _generate_header(command_string)
    print(header)

    output, exit_code = _execute_and_stream(command_string)

    _save_capture(header, output)
    
    return exit_code

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cap.py <command>")
        print('Example: python cap.py python main.py --discover "Dhaka" --quantity 5')
        sys.exit(1)
    
    exit_code = capture_command(sys.argv[1:])
    sys.exit(exit_code)
