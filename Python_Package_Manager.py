#!/usr/bin/env python3
"""
Python Package Manager - Lists, updates, and removes Python packages
with interactive menu, colorful output, and loading animations.
"""

import subprocess
import sys
import json
import time
import os
import re
import shutil
from typing import List, Dict, Any, Optional, Tuple

# Check if colorama is available, otherwise fallback to ANSI codes
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class Colors:
    """Color codes for terminal output."""
    if COLORAMA_AVAILABLE:
        HEADER = Fore.LIGHTBLUE_EX + Style.BRIGHT
        SUCCESS = Fore.GREEN
        WARNING = Fore.YELLOW
        ERROR = Fore.RED
        INFO = Fore.BLUE
        PROCESSING = Fore.YELLOW
        BOLD = Style.BRIGHT
        RESET = Style.RESET_ALL
    else:
        HEADER = '\033[1;94m'
        SUCCESS = '\033[0;32m'
        WARNING = '\033[0;33m'
        ERROR = '\033[0;31m'
        INFO = '\033[0;34m'
        PROCESSING = '\033[0;33m'
        BOLD = '\033[1m'
        RESET = '\033[0m'


class Spinner:
    """Simple loading spinner animation for terminal."""
    def __init__(self, message="Loading..."):
        self.message = message
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.running = False
        self.spinner_thread = None
        self.current_frame = 0
        
    def spin(self):
        """Display the spinner animation."""
        while self.running:
            frame = self.frames[self.current_frame]
            sys.stdout.write(f"\r{Colors.PROCESSING}{frame} {self.message}{Colors.RESET}")
            sys.stdout.flush()
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            time.sleep(0.1)
    
    def start(self):
        """Start the spinner animation."""
        self.running = True
        import threading
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.daemon = True
        self.spinner_thread.start()
    
    def stop(self):
        """Stop the spinner animation."""
        self.running = False
        if self.spinner_thread:
            self.spinner_thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()


def get_terminal_width() -> int:
    """Get the width of the terminal window."""
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ImportError, IOError):
        return 80  # Default width if unable to determine


def print_centered(text: str, color: str = Colors.HEADER) -> None:
    """Print text centered in the terminal with specified color."""
    terminal_width = get_terminal_width()
    lines = text.split('\n')
    for line in lines:
        padding = (terminal_width - len(line)) // 2
        if padding < 0:
            padding = 0
        print(f"{color}{' ' * padding}{line}{Colors.RESET}")


def print_header():
    """Print a styled header for the script, centered in the terminal."""
    header = """
╭──────────────────────────────────────────────╮
│                                              │
│           Python Package Manager             │
│                                              │
│    List, Update, and Remove pip packages     │
│                                              │
╰──────────────────────────────────────────────╯
"""
    print("\n")
    print_centered(header, Colors.HEADER)


def log(message: str, level: str = "info") -> None:
    """
    Log a message with the specified level and color.
    
    Args:
        message: The message to log
        level: The log level (info, success, warning, error, processing)
    """
    timestamp = time.strftime("%H:%M:%S")
    
    if level == "info":
        print(f"{Colors.INFO}[{timestamp}] ℹ {message}{Colors.RESET}")
    elif level == "success":
        print(f"{Colors.SUCCESS}[{timestamp}] ✓ {message}{Colors.RESET}")
    elif level == "warning":
        print(f"{Colors.WARNING}[{timestamp}] ⚠ {message}{Colors.RESET}")
    elif level == "error":
        print(f"{Colors.ERROR}[{timestamp}] ✗ {message}{Colors.RESET}")
    elif level == "processing":
        print(f"{Colors.PROCESSING}[{timestamp}] ⟳ {message}{Colors.RESET}")
    else:
        print(f"[{timestamp}] {message}")


def run_command(command: List[str], timeout: int = 120) -> Dict[str, Any]:
    """
    Run a shell command and return the output.
    
    Args:
        command: The command to run as a list of strings
        timeout: Maximum time in seconds to wait for the command to complete
        
    Returns:
        Dictionary containing stdout, stderr, and return code
    """
    result = {"success": False, "stdout": "", "stderr": "", "returncode": -1}
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        
        result["stdout"] = stdout
        result["stderr"] = stderr
        result["returncode"] = process.returncode
        result["success"] = process.returncode == 0
        
    except subprocess.TimeoutExpired:
        log(f"Command timed out after {timeout} seconds: {' '.join(command)}", "error")
        try:
            process.kill()
        except Exception as e:
            log(f"Failed to kill process: {e}", "error")
    except Exception as e:
        log(f"Error running command: {e}", "error")
        
    return result


def get_pip_path() -> Optional[str]:
    """
    Find the path to the pip executable being used.
    
    Returns:
        Path to pip executable or None if not found
    """
    spinner = Spinner("Locating pip executable")
    spinner.start()
    
    # Try different pip commands to find one that works
    for pip_cmd in ["pip", "pip3", sys.executable + " -m pip"]:
        if " " in pip_cmd:
            cmd = pip_cmd.split() + ["--version"]
        else:
            cmd = [pip_cmd, "--version"]
            
        result = run_command(cmd)
        if result["success"]:
            spinner.stop()
            log(f"Using {pip_cmd}: {result['stdout'].strip()}")
            return pip_cmd
    
    spinner.stop()
    log("Could not find pip. Please ensure pip is installed.", "error")
    return None


def get_outdated_packages() -> List[Dict[str, str]]:
    """
    Get a list of outdated packages.
    
    Returns:
        List of dictionaries containing package information
    """
    pip_cmd = get_pip_path()
    if not pip_cmd:
        return []
        
    spinner = Spinner("Checking for outdated packages")
    spinner.start()
    
    if " " in pip_cmd:
        cmd = pip_cmd.split() + ["list", "--outdated", "--format=json"]
    else:
        cmd = [pip_cmd, "list", "--outdated", "--format=json"]
        
    result = run_command(cmd)
    spinner.stop()
    
    if not result["success"]:
        log(f"Failed to get outdated packages: {result['stderr']}", "error")
        return []
    
    try:
        outdated = json.loads(result["stdout"])
        if outdated:
            log(f"Found {len(outdated)} outdated package(s)", "info")
        else:
            log("All packages are up to date!", "success")
        return outdated
    except json.JSONDecodeError:
        log(f"Failed to parse pip output: {result['stdout']}", "error")
        return []


def get_installed_packages() -> List[Dict[str, str]]:
    """
    Get a list of all installed packages.
    
    Returns:
        List of dictionaries containing package information
    """
    pip_cmd = get_pip_path()
    if not pip_cmd:
        return []
        
    spinner = Spinner("Getting installed packages")
    spinner.start()
    
    if " " in pip_cmd:
        cmd = pip_cmd.split() + ["list", "--format=json"]
    else:
        cmd = [pip_cmd, "list", "--format=json"]
        
    result = run_command(cmd)
    spinner.stop()
    
    if not result["success"]:
        log(f"Failed to get installed packages: {result['stderr']}", "error")
        return []
    
    try:
        packages = json.loads(result["stdout"])
        if packages:
            log(f"Found {len(packages)} installed package(s)", "info")
        else:
            log("No packages are installed!", "warning")
        return packages
    except json.JSONDecodeError:
        log(f"Failed to parse pip output: {result['stdout']}", "error")
        return []


def update_package(package_name: str, pip_cmd: str) -> Tuple[bool, str]:
    """
    Update a single package to the latest version.
    
    Args:
        package_name: Name of the package to update
        pip_cmd: The pip command to use
        
    Returns:
        Tuple of (success, output)
    """
    spinner = Spinner(f"Updating {package_name}")
    spinner.start()
    
    if " " in pip_cmd:
        cmd = pip_cmd.split() + ["install", "--upgrade", package_name]
    else:
        cmd = [pip_cmd, "install", "--upgrade", package_name]
        
    result = run_command(cmd, timeout=300)  # Allow longer timeout for installations
    spinner.stop()
    
    if result["success"]:
        # Extract version from pip output
        version_info = ""
        for line in result["stdout"].splitlines():
            if "Successfully installed" in line:
                version_info = line.strip()
                break
        
        return True, version_info
    else:
        return False, result["stderr"]


def remove_package(package_name: str, pip_cmd: str) -> Tuple[bool, str]:
    """
    Remove a package.
    
    Args:
        package_name: Name of the package to remove
        pip_cmd: The pip command to use
        
    Returns:
        Tuple of (success, output)
    """
    spinner = Spinner(f"Removing {package_name}")
    spinner.start()
    
    if " " in pip_cmd:
        cmd = pip_cmd.split() + ["uninstall", "-y", package_name]
    else:
        cmd = [pip_cmd, "uninstall", "-y", package_name]
        
    result = run_command(cmd, timeout=120)
    spinner.stop()
    
    if result["success"]:
        return True, result["stdout"]
    else:
        return False, result["stderr"]


def display_packages(packages: List[Dict[str, str]], title: str) -> None:
    """
    Display a list of packages with their details.
    
    Args:
        packages: List of package information dictionaries
        title: Title to display above the list
    """
    if not packages:
        log("No packages to display", "warning")
        return
        
    terminal_width = get_terminal_width()
    
    print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
    print("─" * terminal_width)
    
    # Determine column widths
    name_width = max([len(pkg["name"]) for pkg in packages] + [10])
    version_width = max([len(pkg.get("version", "")) for pkg in packages] + [10])
    
    # Header
    print(f"{Colors.BOLD}{'#':<4} {'Package Name':<{name_width}} {'Version':<{version_width}} Description{Colors.RESET}")
    print("─" * terminal_width)
    
    # Package rows
    for i, pkg in enumerate(packages):
        name = pkg["name"]
        version = pkg.get("version", "N/A")
        description = pkg.get("latest_version", "") if "latest_version" in pkg else ""
        
        if not description and "summary" in pkg:
            description = pkg["summary"][:terminal_width - name_width - version_width - 10]
            
        print(f"{i+1:<4} {name:<{name_width}} {version:<{version_width}} {description}")
    
    print("─" * terminal_width)


def display_outdated_packages(packages: List[Dict[str, str]]) -> None:
    """
    Display a list of outdated packages with current and latest versions.
    
    Args:
        packages: List of outdated package information dictionaries
    """
    if not packages:
        log("No outdated packages to display", "success")
        return
        
    terminal_width = get_terminal_width()
    
    print(f"\n{Colors.BOLD}OUTDATED PACKAGES{Colors.RESET}")
    print("─" * terminal_width)
    
    # Determine column widths
    name_width = max([len(pkg["name"]) for pkg in packages] + [10])
    version_width = 10
    
    # Header
    print(f"{Colors.BOLD}{'#':<4} {'Package Name':<{name_width}} {'Current':<{version_width}} {'Latest':<{version_width}} Description{Colors.RESET}")
    print("─" * terminal_width)
    
    # Package rows
    for i, pkg in enumerate(packages):
        name = pkg["name"]
        current = pkg.get("version", "N/A")
        latest = pkg.get("latest_version", "N/A")
        summary = pkg.get("summary", "")[:terminal_width - name_width - version_width*2 - 15]
            
        print(f"{i+1:<4} {name:<{name_width}} {current:<{version_width}} {latest:<{version_width}} {summary}")
    
    print("─" * terminal_width)


def display_summary(successful: List[str], failed: List[str]) -> None:
    """
    Display a summary of the update process.
    
    Args:
        successful: List of successfully updated packages
        failed: List of packages that failed to update
    """
    terminal_width = get_terminal_width()
    
    print("\n" + "─" * terminal_width)
    print(f"{Colors.BOLD}PACKAGE UPDATE SUMMARY{Colors.RESET}")
    print("─" * terminal_width)
    
    if successful:
        print(f"\n{Colors.SUCCESS}✓ Successfully updated ({len(successful)}):{Colors.RESET}")
        for pkg in successful:
            print(f"  • {pkg}")
    
    if failed:
        print(f"\n{Colors.ERROR}✗ Failed to update ({len(failed)}):{Colors.RESET}")
        for pkg in failed:
            print(f"  • {pkg}")
    
    success_rate = len(successful) / (len(successful) + len(failed)) * 100 if successful or failed else 100
    print("\n" + "─" * terminal_width)
    print(f"Update completion rate: {success_rate:.1f}%")
    print("─" * terminal_width)


def wait_for_enter(message: str = "Press Enter to continue...") -> None:
    """
    Wait for the user to press Enter.
    
    Args:
        message: Message to display to the user
    """
    input(f"\n{Colors.INFO}{message}{Colors.RESET}")


def update_all_packages() -> None:
    """Update all outdated packages and display summary."""
    # Get pip path
    pip_cmd = get_pip_path()
    if not pip_cmd:
        return
        
    # Get outdated packages
    outdated_packages = get_outdated_packages()
    
    if not outdated_packages:
        log("No packages to update or package check failed", "info")
        wait_for_enter()
        return
    
    # Display outdated packages
    display_outdated_packages(outdated_packages)
    
    # Ask for confirmation
    wait_for_enter("Press Enter to start updating all packages...")
            
    # Track results
    successful_updates = []
    failed_updates = []
    
    # Update each package
    print(f"\n{Colors.BOLD}UPDATING PACKAGES{Colors.RESET}")
    print("─" * get_terminal_width())
    
    for package_info in outdated_packages:
        package_name = package_info["name"]
        current_version = package_info["version"]
        latest_version = package_info["latest_version"]
        
        log(f"Package: {package_name} (Current: {current_version}, Latest: {latest_version})", "processing")
        
        # Add a small delay between package installations to avoid race conditions
        if outdated_packages.index(package_info) > 0:
            time.sleep(1)
            
        success, output = update_package(package_name, pip_cmd)
        
        if success:
            successful_updates.append(f"{package_name} ({current_version} → {latest_version})")
            log(f"Updated {package_name} to {latest_version}", "success")
        else:
            failed_updates.append(f"{package_name} - {output[:50]}..." if len(output) > 50 else f"{package_name} - {output}")
            log(f"Failed to update {package_name}", "error")
        
        print("─" * get_terminal_width())
            
    # Report results
    display_summary(successful_updates, failed_updates)
    
    # Wait for user to press Enter before continuing
    wait_for_enter()


def list_all_packages() -> None:
    """List all installed packages."""
    packages = get_installed_packages()
    display_packages(packages, "INSTALLED PACKAGES")
    wait_for_enter()


def remove_packages() -> None:
    """Remove packages selected by the user."""
    # Get installed packages
    packages = get_installed_packages()
    if not packages:
        return
    
    # Display packages
    display_packages(packages, "INSTALLED PACKAGES")
    
    # Get package numbers to remove
    while True:
        choice = input(f"\n{Colors.INFO}Enter package number(s) to remove (comma-separated) or 'q' to return: {Colors.RESET}")
        
        if choice.lower() == 'q':
            return
        
        try:
            # Parse comma-separated numbers
            pkg_indices = [int(num.strip()) for num in choice.split(',') if num.strip()]
            
            # Validate indices
            valid_indices = []
            for idx in pkg_indices:
                if 1 <= idx <= len(packages):
                    valid_indices.append(idx)
                else:
                    log(f"Invalid package number: {idx}", "error")
            
            if not valid_indices:
                log("No valid package numbers provided", "error")
                continue
            
            break
        except ValueError:
            log("Please enter valid numbers separated by commas", "error")
    
    # Get pip path
    pip_cmd = get_pip_path()
    if not pip_cmd:
        return
    
    # Remove selected packages
    print(f"\n{Colors.BOLD}REMOVING PACKAGES{Colors.RESET}")
    print("─" * get_terminal_width())
    
    successful_removals = []
    failed_removals = []
    
    for idx in valid_indices:
        package_name = packages[idx-1]["name"]
        
        log(f"Removing package: {package_name}", "processing")
        
        success, output = remove_package(package_name, pip_cmd)
        
        if success:
            successful_removals.append(package_name)
            log(f"Successfully removed {package_name}", "success")
        else:
            failed_removals.append(f"{package_name} - {output[:50]}..." if len(output) > 50 else f"{package_name} - {output}")
            log(f"Failed to remove {package_name}", "error")
        
        print("─" * get_terminal_width())
    
    # Display summary
    print("\n" + "─" * get_terminal_width())
    print(f"{Colors.BOLD}PACKAGE REMOVAL SUMMARY{Colors.RESET}")
    print("─" * get_terminal_width())
    
    if successful_removals:
        print(f"\n{Colors.SUCCESS}✓ Successfully removed ({len(successful_removals)}):{Colors.RESET}")
        for pkg in successful_removals:
            print(f"  • {pkg}")
    
    if failed_removals:
        print(f"\n{Colors.ERROR}✗ Failed to remove ({len(failed_removals)}):{Colors.RESET}")
        for pkg in failed_removals:
            print(f"  • {pkg}")
    
    print("─" * get_terminal_width())
    wait_for_enter()


def display_menu() -> None:
    """Display the main menu and handle user choices."""
    menu_options = [
        "List all installed packages",
        "Check for outdated packages",
        "Update all outdated packages",
        "Remove specific packages",
        "Exit"
    ]
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header()
        
        print(f"\n{Colors.BOLD}MAIN MENU{Colors.RESET}")
        print("─" * get_terminal_width())
        
        for i, option in enumerate(menu_options, 1):
            print(f"{Colors.INFO}{i}.{Colors.RESET} {option}")
        
        print("─" * get_terminal_width())
        
        try:
            choice = input(f"\n{Colors.INFO}Enter your choice (1-{len(menu_options)}): {Colors.RESET}")
            
            if choice == '1':
                list_all_packages()
            elif choice == '2':
                outdated = get_outdated_packages()
                display_outdated_packages(outdated)
                wait_for_enter()
            elif choice == '3':
                update_all_packages()
            elif choice == '4':
                remove_packages()
            elif choice == '5':
                print(f"\n{Colors.SUCCESS}Thank you for using Python Package Manager. Goodbye!{Colors.RESET}")
                break
            else:
                log(f"Invalid choice: {choice}. Please enter a number between 1 and {len(menu_options)}", "error")
                wait_for_enter()
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Operation cancelled.{Colors.RESET}")
            wait_for_enter()
        except Exception as e:
            log(f"An error occurred: {e}", "error")
            wait_for_enter()


def main():
    """Main function to run the package manager."""
    try:
        # Handle terminal colors for Windows
        if os.name == "nt" and not COLORAMA_AVAILABLE:
            os.system("color")
            
        display_menu()
    
    except KeyboardInterrupt:
        print("\n")
        log("Process interrupted by user", "warning")
    except Exception as e:
        log(f"An unexpected error occurred: {e}", "error")


if __name__ == "__main__":
    main()