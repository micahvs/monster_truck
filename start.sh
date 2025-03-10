#!/bin/bash
# Monster Truck Stadium - Server Startup Script

# Define colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HTTP_PORT=8080
WS_PORT=8765
SERVER_PID_FILE=".server.pid"

# Function to check if dependencies are installed
check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    # Check if python3 is installed
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
        exit 1
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        echo -e "${RED}Error: pip is required but not installed.${NC}"
        exit 1
    fi
    
    # Check if websockets is installed
    PIP_CMD="pip3"
    if ! command -v pip3 &> /dev/null; then
        PIP_CMD="pip"
    fi
    
    if ! $PIP_CMD list | grep -q websockets; then
        echo -e "${YELLOW}Installing websockets module...${NC}"
        $PIP_CMD install -r requirements.txt
    fi
    
    echo -e "${GREEN}All dependencies are satisfied.${NC}"
}

# Function to start the server
start_server() {
    echo -e "${BLUE}Starting Monster Truck Stadium server...${NC}"
    
    # Check if server is already running
    if [ -f "$SERVER_PID_FILE" ]; then
        OLD_PID=$(cat "$SERVER_PID_FILE")
        if ps -p $OLD_PID > /dev/null; then
            echo -e "${YELLOW}Server already running with PID $OLD_PID${NC}"
            echo -e "${YELLOW}Use './start.sh restart' to restart the server${NC}"
            return 1
        else
            echo -e "${YELLOW}Removing stale PID file${NC}"
            rm "$SERVER_PID_FILE"
        fi
    fi
    
    # Make sure the script is executable
    chmod +x server.py
    
    # Start the server
    python3 server.py > server.log 2>&1 &
    SERVER_PID=$!
    
    # Save the PID
    echo $SERVER_PID > "$SERVER_PID_FILE"
    
    # Check if server started successfully
    sleep 2
    if ps -p $SERVER_PID > /dev/null; then
        echo -e "${GREEN}Server started with PID: $SERVER_PID${NC}"
        echo -e "${GREEN}HTTP server running on http://localhost:$HTTP_PORT${NC}"
        echo -e "${GREEN}WebSocket server running on ws://localhost:$WS_PORT${NC}"
        return 0
    else
        echo -e "${RED}Failed to start server. Check server.log for details.${NC}"
        return 1
    fi
}

# Function to stop the server
stop_server() {
    echo -e "${BLUE}Stopping Monster Truck Stadium server...${NC}"
    
    # Check if PID file exists
    if [ ! -f "$SERVER_PID_FILE" ]; then
        echo -e "${YELLOW}No server running (PID file not found)${NC}"
        return 0
    fi
    
    # Get the PID
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    
    # Check if process exists
    if ! ps -p $SERVER_PID > /dev/null; then
        echo -e "${YELLOW}Server not running (PID $SERVER_PID not found)${NC}"
        rm "$SERVER_PID_FILE"
        return 0
    fi
    
    # Stop the server
    echo -e "${BLUE}Sending SIGTERM to PID $SERVER_PID${NC}"
    kill -TERM $SERVER_PID
    
    # Wait for server to stop
    TIMEOUT=10
    for i in $(seq 1 $TIMEOUT); do
        if ! ps -p $SERVER_PID > /dev/null; then
            echo -e "${GREEN}Server stopped${NC}"
            rm "$SERVER_PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if server didn't stop
    echo -e "${YELLOW}Server did not stop gracefully, forcing termination...${NC}"
    kill -9 $SERVER_PID
    rm "$SERVER_PID_FILE"
    echo -e "${GREEN}Server terminated${NC}"
}

# Function to restart the server
restart_server() {
    echo -e "${BLUE}Restarting Monster Truck Stadium server...${NC}"
    stop_server
    sleep 2
    start_server
}

# Function to open the game in a browser
open_game() {
    echo -e "${BLUE}Opening game in browser...${NC}"
    
    URL="http://localhost:$HTTP_PORT/"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$URL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "$URL"
        else
            echo -e "${YELLOW}Could not open browser automatically. Please open:${NC}"
            echo -e "${GREEN}$URL${NC}"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows with Git Bash or similar
        start "$URL"
    else
        echo -e "${YELLOW}Could not detect OS to open browser. Please open:${NC}"
        echo -e "${GREEN}$URL${NC}"
    fi
}

# Function to display status
show_status() {
    echo -e "${BLUE}Checking Monster Truck Stadium server status...${NC}"
    
    # Check if PID file exists
    if [ ! -f "$SERVER_PID_FILE" ]; then
        echo -e "${YELLOW}No server running (PID file not found)${NC}"
        return 1
    fi
    
    # Get the PID
    SERVER_PID=$(cat "$SERVER_PID_FILE")
    
    # Check if process exists
    if ps -p $SERVER_PID > /dev/null; then
        echo -e "${GREEN}Server is running with PID $SERVER_PID${NC}"
        echo -e "${GREEN}HTTP server running on http://localhost:$HTTP_PORT${NC}"
        echo -e "${GREEN}WebSocket server running on ws://localhost:$WS_PORT${NC}"
        return 0
    else
        echo -e "${RED}Server not running (PID file exists but process not found)${NC}"
        echo -e "${YELLOW}Removing stale PID file${NC}"
        rm "$SERVER_PID_FILE"
        return 1
    fi
}

# Function to display help
show_help() {
    echo -e "${BLUE}Monster Truck Stadium - Server Management Script${NC}"
    echo
    echo -e "Usage: ${YELLOW}./start.sh [command]${NC}"
    echo
    echo -e "Commands:"
    echo -e "  ${GREEN}start${NC}    - Start the server"
    echo -e "  ${GREEN}stop${NC}     - Stop the server"
    echo -e "  ${GREEN}restart${NC}  - Restart the server"
    echo -e "  ${GREEN}status${NC}   - Show server status"
    echo -e "  ${GREEN}play${NC}     - Open the game in a browser (starts server if needed)"
    echo -e "  ${GREEN}help${NC}     - Show this help message"
    echo
    echo -e "If no command is provided, the server will start and the game will open."
    echo
}

# Main script execution
case "$1" in
    start)
        check_dependencies
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        check_dependencies
        restart_server
        ;;
    status)
        show_status
        ;;
    play)
        check_dependencies
        show_status || start_server
        open_game
        ;;
    help)
        show_help
        ;;
    *)
        # Default: start server and open game
        check_dependencies
        start_server && open_game
        
        # Setup trap to stop server on script exit
        trap stop_server INT
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
        
        # Keep script running to allow for Ctrl+C to stop server
        while true; do
            sleep 1
        done
        ;;
esac