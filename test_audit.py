"""
Fix-It AI - Video Audit Test Script
Tests the move-in and move-out audit endpoints against the local backend.

Usage:
    python test_audit.py

Requirements:
    - Backend running on http://localhost:8000
    - pip install requests
"""

import requests
import json
import os
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
UNIT_ID = "101"

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_json(data, indent=2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def check_backend_health():
    """Verify the backend is running."""
    print_info(f"Checking backend health at {BASE_URL}...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend is healthy: {data.get('status')}")
            print_info(f"API configured: {data.get('api_configured')}")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to backend. Is it running?")
        print_info("Start the backend with: cd backend && uvicorn main:app --reload")
        return False
    except Exception as e:
        print_error(f"Error checking backend: {e}")
        return False


def create_dummy_video():
    """
    Create a minimal valid MP4 file for testing.
    This creates a tiny but valid MP4 container.
    """
    # Minimal valid MP4 file bytes (ftyp + moov atoms)
    # This is a valid but empty MP4 container
    mp4_bytes = bytes([
        # ftyp atom (file type)
        0x00, 0x00, 0x00, 0x14,  # size: 20 bytes
        0x66, 0x74, 0x79, 0x70,  # type: 'ftyp'
        0x69, 0x73, 0x6F, 0x6D,  # major_brand: 'isom'
        0x00, 0x00, 0x00, 0x01,  # minor_version: 1
        0x69, 0x73, 0x6F, 0x6D,  # compatible_brands: 'isom'
        # moov atom (movie header - minimal)
        0x00, 0x00, 0x00, 0x08,  # size: 8 bytes
        0x6D, 0x6F, 0x6F, 0x76,  # type: 'moov'
    ])
    return mp4_bytes


def create_test_image():
    """
    Create a simple test PNG image (1x1 pixel, red).
    """
    # Minimal valid PNG file (1x1 red pixel)
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE,
        0xD4, 0xEF, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
        0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return png_bytes


def test_move_in_audit(video_path=None):
    """
    Test the move-in audit endpoint.
    Creates a baseline for the unit.
    """
    print_header(f"MOVE-IN AUDIT - Unit {UNIT_ID}")
    
    # Prepare the video file
    if video_path and os.path.exists(video_path):
        print_info(f"Using provided video: {video_path}")
        with open(video_path, 'rb') as f:
            video_data = f.read()
        filename = os.path.basename(video_path)
        content_type = 'video/mp4'
    else:
        print_info("Creating dummy video file for testing...")
        video_data = create_dummy_video()
        filename = "move_in_test.mp4"
        content_type = 'video/mp4'
    
    # Make the request
    print_info(f"Uploading to /audit/move-in with unit_id={UNIT_ID}...")
    
    try:
        files = {
            'video': (filename, video_data, content_type)
        }
        data = {
            'unit_id': UNIT_ID
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/move-in",
            files=files,
            data=data,
            timeout=120  # Video processing can take time
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Move-in audit completed successfully!")
            
            print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
            print_json(result)
            
            # Extract key info
            if result.get('success'):
                print(f"\n{Colors.GREEN}{Colors.BOLD}Baseline Summary:{Colors.ENDC}")
                if result.get('unit_summary'):
                    print(f"  {result['unit_summary']}")
                if result.get('baseline_description'):
                    print(f"\n{Colors.CYAN}Baseline Description (stored for comparison):{Colors.ENDC}")
                    desc = result['baseline_description']
                    # Truncate if too long
                    if len(desc) > 500:
                        print(f"  {desc[:500]}...")
                    else:
                        print(f"  {desc}")
                if result.get('existing_damage'):
                    print(f"\n{Colors.YELLOW}Pre-existing Damage Noted:{Colors.ENDC}")
                    for damage in result['existing_damage']:
                        print(f"  • {damage}")
            
            return result
        else:
            print_error(f"Request failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print_error("Request timed out. Video processing may take longer.")
        return None
    except Exception as e:
        print_error(f"Error during move-in audit: {e}")
        return None


def test_move_out_audit(video_path=None):
    """
    Test the move-out audit endpoint.
    Compares against the baseline and identifies new damages.
    """
    print_header(f"MOVE-OUT AUDIT - Unit {UNIT_ID}")
    
    # Prepare the video file
    if video_path and os.path.exists(video_path):
        print_info(f"Using provided video: {video_path}")
        with open(video_path, 'rb') as f:
            video_data = f.read()
        filename = os.path.basename(video_path)
        content_type = 'video/mp4'
    else:
        print_info("Creating dummy video file for testing...")
        video_data = create_dummy_video()
        filename = "move_out_test.mp4"
        content_type = 'video/mp4'
    
    # Make the request
    print_info(f"Uploading to /audit/move-out with unit_id={UNIT_ID}...")
    
    try:
        files = {
            'video': (filename, video_data, content_type)
        }
        data = {
            'unit_id': UNIT_ID
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/move-out",
            files=files,
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Move-out audit completed successfully!")
            
            print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
            print_json(result)
            
            # Print the New Damage Report
            print_new_damage_report(result)
            
            return result
        elif response.status_code == 404:
            print_error("No baseline found for this unit!")
            print_info("Run move-in audit first to create a baseline.")
            return None
        else:
            print_error(f"Request failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print_error("Request timed out. Video processing may take longer.")
        return None
    except Exception as e:
        print_error(f"Error during move-out audit: {e}")
        return None


def print_new_damage_report(result):
    """Print a formatted New Damage Report."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.RED}        NEW DAMAGE REPORT - Unit {UNIT_ID}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    if not result.get('success'):
        print_error(f"Audit failed: {result.get('error', 'Unknown error')}")
        return
    
    # Overall comparison
    comparison = result.get('comparison_result', 'Unknown')
    print(f"{Colors.BOLD}Overall Condition:{Colors.ENDC} {comparison}")
    
    # Unit summary
    if result.get('unit_summary'):
        print(f"{Colors.BOLD}Summary:{Colors.ENDC} {result['unit_summary']}")
    
    # New damages
    new_damages = result.get('new_damages', [])
    print(f"\n{Colors.BOLD}New Damages Found:{Colors.ENDC} {len(new_damages)}")
    
    if new_damages:
        print(f"\n{Colors.RED}{'─'*50}{Colors.ENDC}")
        for i, damage in enumerate(new_damages, 1):
            print(f"\n{Colors.YELLOW}Damage #{i}{Colors.ENDC}")
            print(f"  Location: {damage.get('location', 'N/A')}")
            print(f"  Description: {damage.get('description', 'N/A')}")
            print(f"  Severity: {damage.get('severity', 'N/A')}")
            wear_tear = "Yes" if damage.get('wear_and_tear') else "No"
            print(f"  Normal Wear & Tear: {wear_tear}")
            print(f"  Est. Repair Cost: {damage.get('estimated_repair_cost', 'N/A')}")
            if damage.get('notes'):
                print(f"  Notes: {damage['notes']}")
        print(f"{Colors.RED}{'─'*50}{Colors.ENDC}")
    else:
        print(f"\n{Colors.GREEN}No new damages found! Unit returned in good condition.{Colors.ENDC}")
    
    # Recommended deductions
    deductions = result.get('deductions_recommended', [])
    if deductions:
        print(f"\n{Colors.BOLD}Recommended Deductions:{Colors.ENDC}")
        for ded in deductions:
            print(f"  • {ded.get('item', 'N/A')}: {ded.get('amount', 'N/A')}")
            print(f"    Justification: {ded.get('justification', 'N/A')}")
    
    # Total deductions
    total = result.get('total_estimated_deductions')
    if total:
        print(f"\n{Colors.BOLD}{Colors.RED}TOTAL ESTIMATED DEDUCTIONS: {total}{Colors.ENDC}")
    
    # Additional notes
    if result.get('notes'):
        print(f"\n{Colors.CYAN}Additional Notes:{Colors.ENDC}")
        print(f"  {result['notes']}")
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def main():
    """Main test runner."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║           FIX-IT AI - VIDEO AUDIT TEST SCRIPT             ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # Check command line arguments for custom video paths
    move_in_video = None
    move_out_video = None
    
    if len(sys.argv) > 1:
        move_in_video = sys.argv[1]
        print_info(f"Using custom move-in video: {move_in_video}")
    if len(sys.argv) > 2:
        move_out_video = sys.argv[2]
        print_info(f"Using custom move-out video: {move_out_video}")
    
    # Step 1: Check backend health
    if not check_backend_health():
        print_error("\nBackend is not available. Exiting.")
        sys.exit(1)
    
    # Step 2: Run Move-In Audit
    print_info("\nStarting Move-In Audit (creates baseline)...")
    move_in_result = test_move_in_audit(move_in_video)
    
    if not move_in_result:
        print_error("\nMove-in audit failed. Cannot proceed with move-out test.")
        print_info("Note: The dummy video may not be processed by Gemini.")
        print_info("For a real test, provide actual video files:")
        print_info("  python test_audit.py <move_in_video.mp4> <move_out_video.mp4>")
        sys.exit(1)
    
    # Step 3: Run Move-Out Audit
    print_info("\nStarting Move-Out Audit (compares against baseline)...")
    move_out_result = test_move_out_audit(move_out_video)
    
    if not move_out_result:
        print_error("\nMove-out audit failed.")
        sys.exit(1)
    
    # Summary
    print_header("TEST COMPLETE")
    print_success("Both move-in and move-out audits completed!")
    print_info(f"Unit ID: {UNIT_ID}")
    print_info("Check the New Damage Report above for results.")


if __name__ == "__main__":
    main()
