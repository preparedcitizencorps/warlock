#!/bin/bash
#
# WARLOCK Raspberry Pi Setup Script
#
# Automates installation and configuration of WARLOCK on Raspberry Pi 5.
# Run this script after flashing Raspberry Pi OS (Desktop or Lite).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/preparedcitizencorps/warlock/master/software/setup_pi.sh | bash
#   OR
#   git clone https://github.com/preparedcitizencorps/warlock.git
#   cd warlock/software
#   chmod +x setup_pi.sh
#   ./setup_pi.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/preparedcitizencorps/warlock.git"
INSTALL_DIR="$HOME/warlock"
PYTHON_VERSION="python3"

# Helper functions
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_warning "This script is designed for Raspberry Pi. Continuing anyway..."
    else
        print_success "Raspberry Pi detected"
    fi
}

# Check for sudo privileges
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        print_info "This script requires sudo privileges. You may be prompted for your password."
    fi
}

# Update system
update_system() {
    print_header "Updating System Packages"

    sudo apt update
    print_success "Package list updated"

    print_info "Upgrading packages (this may take a while)..."
    sudo apt upgrade -y
    print_success "System packages upgraded"
}

# Install core dependencies
install_core_dependencies() {
    print_header "Installing Core Dependencies"

    local packages=(
        "python3"
        "python3-pip"
        "python3-opencv"
        "python3-picamera2"  # Official Pi camera library
        "git"
        "libgl1"
        "libglib2.0-0"
        "v4l-utils"  # Video4Linux utilities for camera detection
    )

    print_info "Installing: ${packages[*]}"
    sudo apt install -y "${packages[@]}"
    print_success "Core dependencies installed"
}

# Install DRM/KMS dependencies (for headless mode)
install_drm_dependencies() {
    print_header "Installing DRM/KMS Dependencies (Headless Mode)"

    local packages=(
        "python3-kms++"  # DRM/KMS display support
        "python3-evdev"  # Keyboard input without X11
    )

    print_info "Installing: ${packages[*]}"
    sudo apt install -y "${packages[@]}"
    print_success "DRM/KMS dependencies installed"
}

# Configure user groups
configure_user_groups() {
    print_header "Configuring User Groups"

    local current_user="$USER"
    local groups_needed=("video" "input")
    local groups_added=()

    for group in "${groups_needed[@]}"; do
        if ! groups "$current_user" | grep -q "\b$group\b"; then
            sudo usermod -a -G "$group" "$current_user"
            groups_added+=("$group")
            print_success "Added user to '$group' group"
        else
            print_info "User already in '$group' group"
        fi
    done

    if [ ${#groups_added[@]} -gt 0 ]; then
        print_warning "Groups added: ${groups_added[*]}"
        print_warning "You must logout/login or reboot for group changes to take effect!"
    fi
}

# Setup udev rules for input devices
setup_udev_rules() {
    print_header "Setting Up udev Rules for Input Devices"

    local rule_file="/etc/udev/rules.d/99-input.rules"
    local rule_content='KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"'

    if [ -f "$rule_file" ]; then
        print_info "udev rule already exists: $rule_file"
    else
        echo "$rule_content" | sudo tee "$rule_file" > /dev/null
        print_success "Created udev rule: $rule_file"

        sudo udevadm control --reload-rules
        sudo udevadm trigger
        print_success "Reloaded udev rules"
    fi
}

# Clone or update repository
setup_repository() {
    print_header "Setting Up WARLOCK Repository"

    if [ -d "$INSTALL_DIR" ]; then
        print_info "Repository already exists at $INSTALL_DIR"
        print_info "Updating repository..."
        cd "$INSTALL_DIR"
        git pull origin master
        print_success "Repository updated"
    else
        print_info "Cloning repository to $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        print_success "Repository cloned"
    fi
}

# Install Python dependencies
install_python_dependencies() {
    print_header "Installing Python Dependencies"

    cd "$INSTALL_DIR/software"

    # Install common requirements
    if [ -f "requirements.txt" ]; then
        print_info "Installing common dependencies..."
        pip3 install -r requirements.txt --break-system-packages
        print_success "Common dependencies installed"
    fi

    # Install YOLO-specific dependencies that ultralytics may miss
    print_info "Installing YOLO tracking dependencies..."
    pip3 install --break-system-packages "lap>=0.5.12"
    print_success "YOLO tracking dependencies installed"
}

# Install Arducam PiVariety camera support (optional)
install_arducam_pivariety() {
    print_header "Arducam PiVariety Camera Support (Optional)"

    print_info "Do you want to install Arducam PiVariety camera support?"
    print_info "This is needed for Arducam low-light cameras (IMX462, IMX327, etc.)"
    echo -n "Install PiVariety support? [y/N]: "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Skipping Arducam PiVariety installation"
        return
    fi

    print_info "Downloading Arducam installation script..."
    cd "$HOME"

    local SCRIPT_URL="https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh"
    local SCRIPT_FILE="install_pivariety_pkgs.sh"
    local EXPECTED_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    if ! wget --timeout=30 -O "$SCRIPT_FILE" "$SCRIPT_URL"; then
        print_error "Failed to download Arducam installation script"
        return 1
    fi

    local ACTUAL_SHA
    ACTUAL_SHA=$(sha256sum "$SCRIPT_FILE" | awk '{print $1}')
    print_info "Downloaded script SHA256: $ACTUAL_SHA"

    if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
        print_warning "SHA256 mismatch detected - script may have been updated"
        print_info "Expected: $EXPECTED_SHA"
        print_info "Actual:   $ACTUAL_SHA"
        print_info "Visit https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver to verify"
        echo -n "Continue anyway? [y/N]: "
        read -r continue_response
        if [[ ! "$continue_response" =~ ^[Yy]$ ]]; then
            print_error "Installation aborted due to SHA256 mismatch"
            rm -f "$SCRIPT_FILE"
            return 1
        fi
    fi

    chmod +x "$SCRIPT_FILE"
    print_success "Downloaded installation script"

    print_info "Installing Arducam libcamera (this may take a few minutes)..."
    ./install_pivariety_pkgs.sh -p libcamera_dev
    print_success "Arducam libcamera installed"

    print_info "Installing Arducam libcamera-apps..."
    ./install_pivariety_pkgs.sh -p libcamera_apps
    print_success "Arducam libcamera-apps installed"

    # Configure camera overlay
    local config_file="/boot/firmware/config.txt"
    if [ -f "$config_file" ]; then
        if ! grep -qE '^[[:space:]]*dtoverlay=arducam-pivariety' "$config_file"; then
            print_info "Configuring camera overlay in $config_file..."

            # Find [all] section and add overlay
            if grep -qE '^[[:space:]]*\[all\]' "$config_file"; then
                sudo sed -i '/^[[:space:]]*\[all\]/a dtoverlay=arducam-pivariety' "$config_file"

                if ! grep -qE '^[[:space:]]*dtoverlay=arducam-pivariety' "$config_file"; then
                    print_error "Failed to add dtoverlay to config.txt"
                    return 1
                fi
                print_success "Added dtoverlay=arducam-pivariety to config.txt"
            else
                echo "" | sudo tee -a "$config_file" > /dev/null
                echo "[all]" | sudo tee -a "$config_file" > /dev/null
                echo "dtoverlay=arducam-pivariety" | sudo tee -a "$config_file" > /dev/null

                if ! grep -qE '^[[:space:]]*dtoverlay=arducam-pivariety' "$config_file"; then
                    print_error "Failed to add dtoverlay to config.txt"
                    return 1
                fi
                print_success "Added [all] section and dtoverlay=arducam-pivariety to config.txt"
            fi

            print_warning "Camera overlay configured - reboot required to take effect"
        else
            print_info "Arducam PiVariety overlay already configured"
        fi
    fi

    # Fix config.txt for proper libcamera operation
    print_info "Checking config.txt for libcamera compatibility..."

    # Remove media-controller=0 parameter if present (breaks libcamera)
    if grep -qE 'dtoverlay=arducam-pivariety,media-controller=0' "$config_file"; then
        print_info "Fixing media-controller parameter in config.txt..."
        sudo sed -i 's/^dtoverlay=arducam-pivariety,media-controller=0$/dtoverlay=arducam-pivariety/' "$config_file"
        print_success "Removed media-controller=0 (enables libcamera support)"
    fi

    # Ensure I2C baudrate is set for IMX462 stability
    if ! grep -qE '^[[:space:]]*dtparam=i2c_arm_baudrate=' "$config_file"; then
        print_info "Setting I2C baudrate for camera stability..."
        if grep -qE '^[[:space:]]*\[all\]' "$config_file"; then
            sudo sed -i '/^[[:space:]]*\[all\]/a dtparam=i2c_arm_baudrate=10000' "$config_file"
        fi
        print_success "Set i2c_arm_baudrate=10000"
    fi

    # Create symlink for IMX462 camera tuning file
    print_info "Creating camera tuning file symlink..."
    local tuning_dir="/usr/share/libcamera/ipa/rpi/pisp"
    if [ -f "$tuning_dir/imx462.json" ]; then
        sudo ln -sf "$tuning_dir/imx462.json" "$tuning_dir/arducam-pivariety.json"
        print_success "Created IMX462 tuning file symlink"
        print_info "IMX462 camera will use optimized tuning parameters"
    else
        print_warning "IMX462 tuning file not found - may need to reboot first"
        print_info "After reboot, run: sudo ln -sf $tuning_dir/imx462.json $tuning_dir/arducam-pivariety.json"
    fi

    print_success "Arducam PiVariety installation complete"
    print_info "IMPORTANT: Connect camera to Camera Port 1 on Raspberry Pi 5"
    print_info "Test camera after reboot with: rpicam-hello --list-cameras"
}

# Configure camera
configure_camera() {
    print_header "Configuring Camera"

    local config_file="/boot/firmware/config.txt"

    if [ ! -f "$config_file" ]; then
        print_warning "Config file not found: $config_file"
        print_warning "Camera configuration may need manual setup"
        return
    fi

    print_info "Camera configuration options:"
    print_info "  • USB cameras: Work out of the box with OpenCV"
    print_info "  • Standard Pi cameras: Auto-detected by default"
    print_info "  • Arducam PiVariety: Requires special installation (see previous step)"

    print_success "Camera configuration checked"
}

# Create convenience scripts
create_convenience_scripts() {
    print_header "Creating Convenience Scripts"

    # Main WARLOCK launcher script
    local launcher_script="$INSTALL_DIR/run_warlock.sh"
    cat > "$launcher_script" << 'EOF'
#!/bin/bash
# Quick launcher for WARLOCK

cd "$(dirname "$0")/software"

# Parse arguments
USE_DRM=0

for arg in "$@"; do
    case $arg in
        --drm|--headless)
            USE_DRM=1
            shift
            ;;
        --help|-h)
            echo "WARLOCK Launcher"
            echo ""
            echo "Usage: ./run_warlock.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --drm, --headless    Use DRM/KMS display (headless mode)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Display Modes:"
            echo "  X11 (default): Displays on SSH client when using 'ssh -X'"
            echo "  DRM: Direct display to connected monitor/AR glasses"
            echo ""
            echo "Examples:"
            echo "  ssh -X pi@warlock.local './run_warlock.sh'"
            echo "  ./run_warlock.sh --drm"
            exit 0
            ;;
    esac
done

# Build command
CMD="python3 main.py"

if [ $USE_DRM -eq 1 ]; then
    CMD="$CMD --use-drm"
fi

# Run
echo "Starting WARLOCK..."
echo "Command: $CMD"
echo ""
$CMD
EOF
    chmod +x "$launcher_script"
    print_success "Created launcher: $launcher_script"
}

# Create systemd service (optional)
create_systemd_service() {
    print_header "Creating Systemd Service (Optional)"

    print_info "Would you like to create a systemd service to auto-start WARLOCK on boot?"
    print_info "This will run WARLOCK in DRM mode at startup."
    echo -n "Create service? [y/N]: "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        local service_file="/etc/systemd/system/warlock.service"

        sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=WARLOCK
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/software
Environment="WARLOCK_USE_DRM=1"
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        print_success "Created systemd service: $service_file"
        print_info "To enable auto-start: sudo systemctl enable warlock"
        print_info "To start now: sudo systemctl start warlock"
        print_info "To view logs: sudo journalctl -u warlock -f"
    else
        print_info "Skipping systemd service creation"
    fi
}

# Test installation
test_installation() {
    print_header "Testing Installation"

    cd "$INSTALL_DIR/software"

    # Test Python imports
    print_info "Testing Python imports..."
    if $PYTHON_VERSION -c "import cv2; import numpy; import yaml" 2>/dev/null; then
        print_success "Core Python imports working"
    else
        print_error "Python import test failed"
        return 1
    fi

    # Test picamera2 (may not be available on all systems)
    if $PYTHON_VERSION -c "from picamera2 import Picamera2" 2>/dev/null; then
        print_success "Picamera2 available"
    else
        print_warning "Picamera2 not available (may need reboot or is not Raspberry Pi)"
    fi

    # Test evdev
    if $PYTHON_VERSION -c "import evdev" 2>/dev/null; then
        print_success "evdev available"
    else
        print_warning "evdev not available"
    fi

    # Check camera detection
    print_info "Checking camera detection..."
    if command -v rpicam-hello &> /dev/null; then
        if rpicam-hello --list-cameras 2>&1 | grep -q "Available cameras"; then
            print_success "Camera detected"
        else
            print_warning "No camera detected (may need camera connected or enabled)"
        fi
    else
        print_info "rpicam-hello not available (old Pi OS version?)"
    fi
}

# Print completion summary
print_completion_summary() {
    print_header "Installation Complete!"

    echo ""
    print_success "WARLOCK has been installed to: $INSTALL_DIR"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  1. Test locally (if using desktop environment):"
    echo "     cd $INSTALL_DIR"
    echo "     ./run_warlock.sh"
    echo ""
    echo "  2. Test with X11 forwarding (display on SSH client):"
    echo "     ssh -X $USER@$(hostname)"
    echo "     cd $INSTALL_DIR"
    echo "     ./run_warlock.sh"
    echo ""
    echo "  3. Test with DRM (headless mode, requires console or VT):"
    echo "     cd $INSTALL_DIR"
    echo "     ./run_warlock.sh --drm"
    echo ""
    echo -e "${BLUE}Display Modes:${NC}"
    echo "  • X11 (default): Use 'ssh -X' to display on remote computer"
    echo "  • DRM: Direct rendering to connected display/AR glasses"
    echo ""
    echo -e "${BLUE}Controls:${NC}"
    echo "  Q - Quit | H - Help | P - Plugin panel"
    echo "  Y - YOLO toggle | F - FPS | M - Map"
    echo ""

    # Check if reboot needed
    if groups "$USER" | grep -q video && groups "$USER" | grep -q input; then
        print_info "All group memberships active"
    else
        print_warning "Group changes require logout/login or reboot to take effect!"
        echo ""
        echo -n "Reboot now? [y/N]: "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_info "Rebooting in 5 seconds... (Ctrl+C to cancel)"
            sleep 5
            sudo reboot
        fi
    fi

    echo ""
    print_info "Documentation: https://github.com/preparedcitizencorps/warlock"
    print_info "Discord: https://discord.gg/uFMEug4Bb9"
    echo ""
}

# Main installation flow
main() {
    print_header "WARLOCK Raspberry Pi Setup"

    check_raspberry_pi
    check_sudo

    echo ""
    print_info "This script will:"
    echo "  • Update system packages"
    echo "  • Install dependencies (OpenCV, picamera2, etc.)"
    echo "  • Configure user groups and permissions"
    echo "  • Clone/update WARLOCK repository"
    echo "  • Install Python dependencies"
    echo "  • Create launcher scripts"
    echo ""
    echo -n "Continue? [Y/n]: "
    read -r response

    if [[ "$response" =~ ^[Nn]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi

    # Run installation steps
    update_system
    install_core_dependencies
    install_drm_dependencies
    configure_user_groups
    setup_udev_rules
    setup_repository
    install_python_dependencies
    install_arducam_pivariety
    configure_camera
    create_convenience_scripts
    create_systemd_service
    test_installation

    # Done!
    print_completion_summary
}

# Run main function
main "$@"
