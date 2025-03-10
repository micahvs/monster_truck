#!/usr/bin/env python3
"""
Monster Truck Stadium - WebSocket Server
A simple but robust WebSocket server for the Monster Truck game
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import traceback
import uuid
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("MonsterTruckServer")

# Global state
CLIENTS = {}  # Store connected clients and their data
GAME_STATE = {
    "trucks": {},
    "obstacles": {},
    "serverInfo": {
        "startTime": None,
        "version": "1.0.1"
    }
}

# Server settings
HTTP_PORT = 8080
WS_PORT = 8765
SERVER_ALIVE = True  # Flag for graceful shutdown

class SimpleHTTPHandler(SimpleHTTPRequestHandler):
    """Simple HTTP handler to serve the game files"""
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        if 'favicon.ico' not in args[0]:  # Skip favicon requests in logs
            logger.info(f"HTTP: {args[0]}")

    def end_headers(self):
        """Add CORS headers to allow WebSocket connections"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')
        SimpleHTTPRequestHandler.end_headers(self)

def run_http_server():
    """Run the HTTP server in a separate thread"""
    try:
        server = HTTPServer(("", HTTP_PORT), SimpleHTTPHandler)
        logger.info(f"HTTP server started on port {HTTP_PORT}")
        
        while SERVER_ALIVE:
            server.handle_request()
            
    except Exception as e:
        logger.error(f"HTTP server error: {str(e)}")
    finally:
        logger.info("HTTP server stopped")

# WebSocket server functions
async def register_client(websocket):
    """Register a new client and assign a unique ID"""
    client_id = str(uuid.uuid4())
    CLIENTS[client_id] = {
        "websocket": websocket,
        "position": {"x": 0, "y": 2, "z": 0},
        "rotation": {"y": 0},
        "speed": 0,
        "color": "#ff00ff",  # Default color
        "nickname": "Player",  # Default nickname
        "score": 0,  # Initialize score
        "connected_at": asyncio.get_event_loop().time()
    }
    logger.info(f"New client connected: {client_id}")
    
    # Send client their ID and initial game state
    try:
        await websocket.send(json.dumps({
            "type": "register",
            "id": client_id,
            "gameState": GAME_STATE
        }))
        
        # Inform all clients about the new player
        await broadcast_new_player(client_id)
    except Exception as e:
        logger.error(f"Error during client registration: {str(e)}")
        # Try to clean up, though it might already be too late
        if client_id in CLIENTS:
            del CLIENTS[client_id]
            
    return client_id

async def unregister_client(client_id):
    """Unregister a client when they disconnect"""
    if client_id in CLIENTS:
        try:
            logger.info(f"Client disconnected: {client_id}")
            del CLIENTS[client_id]
            
            # Remove from game state
            if client_id in GAME_STATE["trucks"]:
                del GAME_STATE["trucks"][client_id]
            
            # Inform all clients about the disconnected player
            await broadcast({
                "type": "playerDisconnect",
                "id": client_id
            })
        except Exception as e:
            logger.error(f"Error during client unregister: {str(e)}")

async def broadcast_new_player(client_id):
    """Broadcast new player to all connected clients"""
    if client_id in CLIENTS:
        try:
            message = {
                "type": "newPlayer",
                "id": client_id,
                "position": CLIENTS[client_id]["position"],
                "rotation": CLIENTS[client_id]["rotation"],
                "color": CLIENTS[client_id]["color"],
                "nickname": CLIENTS[client_id].get("nickname", "Player"),
                "score": CLIENTS[client_id].get("score", 0)
            }
            await broadcast(message)
        except Exception as e:
            logger.error(f"Error broadcasting new player: {str(e)}")

async def broadcast(message):
    """Broadcast a message to all connected clients"""
    if not CLIENTS:
        return
        
    try:
        message_str = json.dumps(message)
        # Create tasks for each send operation
        tasks = []
        
        for client_id, client_data in list(CLIENTS.items()):
            try:
                websocket = client_data["websocket"]
                # Check if the connection is still open
                if websocket.open:
                    tasks.append(asyncio.create_task(websocket.send(message_str)))
                else:
                    # Connection already closed, clean up
                    logger.warning(f"Removing stale client connection: {client_id}")
                    if client_id in CLIENTS:
                        del CLIENTS[client_id]
            except Exception as e:
                logger.error(f"Error preparing broadcast to client {client_id}: {str(e)}")
                # Try to remove the problematic client
                if client_id in CLIENTS:
                    del CLIENTS[client_id]
        
        # Wait for all sends to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    except Exception as e:
        logger.error(f"Broadcast error: {str(e)}")

async def handle_message(websocket, client_id, message):
    """Handle messages from clients"""
    try:
        data = json.loads(message)
        message_type = data.get("type", "unknown")
        
        if message_type == "updatePosition":
            # Update client position and broadcast to others
            CLIENTS[client_id]["position"] = data["position"]
            CLIENTS[client_id]["rotation"] = data["rotation"]
            CLIENTS[client_id]["speed"] = data.get("speed", 0)
            
            # Update game state
            GAME_STATE["trucks"][client_id] = {
                "position": data["position"],
                "rotation": data["rotation"],
                "speed": data.get("speed", 0),
                "color": CLIENTS[client_id]["color"],
                "nickname": CLIENTS[client_id].get("nickname", "Player")
            }
            
            # Broadcast position update to all other clients
            await broadcast({
                "type": "playerMove",
                "id": client_id,
                "position": data["position"],
                "rotation": data["rotation"],
                "speed": data.get("speed", 0)
            })
        
        elif message_type == "obstacleDestroyed":
            # Handle obstacle destruction
            obstacle_id = data["obstacleId"]
            GAME_STATE["obstacles"][obstacle_id] = {
                "destroyed": True,
                "destroyedBy": client_id
            }
            
            # Broadcast obstacle destruction to all clients
            await broadcast({
                "type": "obstacleDestroyed",
                "obstacleId": obstacle_id,
                "destroyedBy": client_id
            })
        
        elif message_type == "scoreUpdate":
            # Update client score and broadcast
            score = data.get("score", 0)
            CLIENTS[client_id]["score"] = score
            
            # Update game state
            if client_id in GAME_STATE["trucks"]:
                GAME_STATE["trucks"][client_id]["score"] = score
            
            await broadcast({
                "type": "scoreUpdate",
                "id": client_id,
                "score": score
            })
        
        elif message_type == "setColor":
            # Update client color
            color = data.get("color", "#ff00ff")
            CLIENTS[client_id]["color"] = color
            
            if client_id in GAME_STATE["trucks"]:
                GAME_STATE["trucks"][client_id]["color"] = color
            
            # Broadcast color change to all clients
            await broadcast({
                "type": "playerColorChange",
                "id": client_id,
                "color": color
            })
        
        elif message_type == "setNickname":
            # Update client nickname
            nickname = data.get("nickname", "Player")
            CLIENTS[client_id]["nickname"] = nickname
            
            if client_id in GAME_STATE["trucks"]:
                GAME_STATE["trucks"][client_id]["nickname"] = nickname
            
            # Broadcast nickname change to all clients
            await broadcast({
                "type": "playerNicknameChange",
                "id": client_id,
                "nickname": nickname
            })
        
        elif message_type == "chatMessage":
            # Validate message content
            message_content = data.get("message", "").strip()
            if message_content and len(message_content) <= 200:  # Limit message length
                # Broadcast chat message to all clients
                await broadcast({
                    "type": "chatMessage",
                    "id": client_id,
                    "message": message_content
                })
            
        elif message_type == "ping":
            # Simple ping response
            try:
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": data.get("timestamp", 0)
                }))
            except Exception as e:
                logger.error(f"Error sending ping response: {str(e)}")
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        logger.error(traceback.format_exc())

async def connection_handler(websocket, path):
    """Handle WebSocket connections"""
    client_id = None
    
    try:
        # Register new client
        client_id = await register_client(websocket)
        
        # Process messages from client
        async for message in websocket:
            if not SERVER_ALIVE:
                break
                
            await handle_message(websocket, client_id, message)
            
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed: {e.code} {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up when client disconnects
        if client_id:
            await unregister_client(client_id)

async def health_check():
    """Periodically check client connections and remove stale ones"""
    while SERVER_ALIVE:
        try:
            # Check each client
            current_time = asyncio.get_event_loop().time()
            stale_clients = []
            
            for client_id, client_data in CLIENTS.items():
                try:
                    websocket = client_data.get("websocket")
                    if websocket and not websocket.open:
                        stale_clients.append(client_id)
                        continue
                        
                    # Check how long the client has been connected
                    connected_at = client_data.get("connected_at", current_time)
                    if current_time - connected_at > 7200:  # 2 hours
                        logger.info(f"Client {client_id} session timeout")
                        stale_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Error checking client {client_id}: {str(e)}")
                    stale_clients.append(client_id)
            
            # Remove stale clients
            for client_id in stale_clients:
                await unregister_client(client_id)
                
            # Log server stats
            if CLIENTS:
                logger.info(f"Active connections: {len(CLIENTS)}")
                
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            
        # Run every minute
        await asyncio.sleep(60)

async def run_server():
    """Start the WebSocket server"""
    # Set up the server
    port = WS_PORT
    host = "0.0.0.0"  # Listen on all interfaces
    
    logger.info(f"WebSocket server starting on {host}:{port}")
    
    # Create the server
    server = await websockets.serve(
        connection_handler, 
        host, 
        port,
        ping_interval=30,  # Send pings every 30 seconds
        ping_timeout=10    # Wait 10 seconds for pong responses
    )
    
    # Schedule health check task
    health_task = asyncio.create_task(health_check())
    
    # Keep the server running until stopped
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        logger.info("WebSocket server shutting down")
    finally:
        # Clean up
        health_task.cancel()
        server.close()
        await server.wait_closed()
        logger.info("WebSocket server stopped")

def handle_shutdown(signal, frame):
    """Handle shutdown signals gracefully"""
    global SERVER_ALIVE
    logger.info("Shutdown signal received, closing server...")
    SERVER_ALIVE = False
    # Give the server some time to clean up
    threading.Timer(2.0, lambda: sys.exit(0)).start()

if __name__ == "__main__":
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Initialize game state with server start time
    import datetime
    GAME_STATE["serverInfo"]["startTime"] = datetime.datetime.now().isoformat()
    
    # Start the WebSocket server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shutdown by keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())