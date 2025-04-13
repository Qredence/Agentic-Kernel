"""Chat Server for the ADK A2A Chat System."""

import asyncio
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from agentic_kernel.communication.coordination import CoordinationManager
from agentic_kernel.communication.trust import TrustManager

from ..agents.creative import CreativeAgent
from ..agents.orchestrator import OrchestratorAgent
from ..agents.reasoning import ReasoningAgent
from ..agents.research import ResearchAgent
from ..utils.adk_a2a_utils import setup_adk_a2a_environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatServer:
    """Chat Server that hosts the chat interface and manages agent communication."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
    ):
        """Initialize the ChatServer.

        Args:
            host: The host for the server
            port: The port for the server
        """
        self.host = host
        self.port = port

        # Set up environment
        setup_adk_a2a_environment()

        # Initialize managers
        self.coordination_manager = CoordinationManager()
        self.trust_manager = TrustManager()

        # Initialize agents
        self.agents = {}
        self.initialize_agents()

        # Initialize active connections
        self.active_connections: list[WebSocket] = []

        # Create Starlette app
        self.app = Starlette(
            debug=True,
            routes=[
                Route("/", self.home, methods=["GET"]),
                Route("/agents", self.get_agents, methods=["GET"]),
                Route("/chat", self.chat, methods=["POST"]),
                WebSocketRoute("/ws", self.websocket_endpoint),
            ],
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["*"],
                    allow_headers=["*"],
                ),
            ],
        )

    def initialize_agents(self) -> None:
        """Initialize the agents."""
        logger.info("Initializing agents...")

        # Create agents
        self.agents["orchestrator"] = OrchestratorAgent(
            coordination_manager=self.coordination_manager,
            trust_manager=self.trust_manager,
            host="localhost",
            port=8000,
        )

        self.agents["research"] = ResearchAgent(
            host="localhost",
            port=8001,
        )

        self.agents["creative"] = CreativeAgent(
            host="localhost",
            port=8002,
        )

        self.agents["reasoning"] = ReasoningAgent(
            host="localhost",
            port=8003,
        )

        # Connect agents to each other
        for agent_name, agent in self.agents.items():
            if agent_name != "orchestrator":
                # Connect specialized agents to orchestrator
                agent.connect_to_agent(
                    agent_name="orchestrator",
                    base_url="http://localhost:8000",
                )
                
                # Connect orchestrator to specialized agents
                self.agents["orchestrator"].connect_to_agent(
                    agent_name=agent_name,
                    base_url=f"http://localhost:{8001 if agent_name == 'research' else 8002 if agent_name == 'creative' else 8003}",
                )

    async def start_agents(self) -> None:
        """Start the agents."""
        logger.info("Starting agents...")
        
        # Start each agent
        for agent_name, agent in self.agents.items():
            await agent.start()
            logger.info(f"Agent {agent_name} started")

    async def home(self, request: Request) -> JSONResponse:
        """Handle the home route.

        Args:
            request: The request

        Returns:
            A JSON response
        """
        return JSONResponse({
            "status": "ok",
            "message": "ADK A2A Chat Server is running",
        })

    async def get_agents(self, request: Request) -> JSONResponse:
        """Handle the agents route.

        Args:
            request: The request

        Returns:
            A JSON response with agent information
        """
        agent_info = {}
        for agent_name, agent in self.agents.items():
            agent_info[agent_name] = {
                "name": agent.name,
                "description": agent.description,
                "model": agent.model,
                "url": f"http://{agent.host}:{agent.port}",
            }
            
        return JSONResponse({
            "status": "ok",
            "agents": agent_info,
        })

    async def chat(self, request: Request) -> JSONResponse:
        """Handle the chat route.

        Args:
            request: The request

        Returns:
            A JSON response with the chat response
        """
        # Parse request
        data = await request.json()
        message = data.get("message", "")
        
        if not message:
            return JSONResponse({
                "status": "error",
                "message": "No message provided",
            }, status_code=400)
            
        # Process message with orchestrator
        try:
            response = await self.agents["orchestrator"].process_user_message(message)
            
            return JSONResponse({
                "status": "ok",
                "response": response["response"],
                "activity_id": response["activity_id"],
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return JSONResponse({
                "status": "error",
                "message": f"Error processing message: {str(e)}",
            }, status_code=500)

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        """Handle WebSocket connections.

        Args:
            websocket: The WebSocket connection
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                message = data.get("message", "")
                
                if not message:
                    await websocket.send_json({
                        "status": "error",
                        "message": "No message provided",
                    })
                    continue
                    
                # Process message with orchestrator
                try:
                    response = await self.agents["orchestrator"].process_user_message(message)
                    
                    await websocket.send_json({
                        "status": "ok",
                        "response": response["response"],
                        "activity_id": response["activity_id"],
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    await websocket.send_json({
                        "status": "error",
                        "message": f"Error processing message: {str(e)}",
                    })
                    
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            
        finally:
            # Remove connection
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def run(self) -> None:
        """Run the chat server."""
        # Start agents
        await self.start_agents()
        
        # Start server
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


async def create_and_run_server(
    host: str = "localhost",
    port: int = 8080,
) -> None:
    """Create and run the chat server.

    Args:
        host: The host for the server
        port: The port for the server
    """
    server = ChatServer(host=host, port=port)
    await server.run()


if __name__ == "__main__":
    asyncio.run(create_and_run_server())