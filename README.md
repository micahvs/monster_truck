# Monster Truck Stadium Multiplayer

A multiplayer monster truck game with 80s synthwave aesthetics.

## Setup Instructions

### Quick Start
1. Make sure you have Python 3.8+ installed
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the start script:
   ```
   bash start.sh
   ```
   This will start the server and open the game in your browser automatically.
   
### Manual Setup

#### Server Setup
1. Start the WebSocket server:
   ```
   python server.py
   ```
   The server will run on port 8765.

#### Client Setup
1. Open the `index.html` file in your web browser
2. Enter your nickname when prompted
3. Select your truck color
4. Drive around with other players in the arena!

## How to Play
- **Controls:**
  - Arrow keys: Drive the truck (Up/Down for acceleration/braking, Left/Right for steering)
  - W/S: Adjust camera height
  - A/D: Adjust camera distance
  - C: Toggle chat window
  - Enter: Send chat message

- **Goal:**
  - Crash into destructible obstacles to score points
  - Drive up ramps for big air jumps
  - Compete for the highest score

## Multiplayer Features
- See other players' trucks in real-time
- Global scoreboard tracking all players
- In-game chat
- Trucks with customizable colors
- Synchronized obstacle destruction