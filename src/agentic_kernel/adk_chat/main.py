"""Main entry point for the ADK A2A Chat System."""

import argparse
import asyncio
import logging

# Import necessary modules
from agentic_kernel.adk_chat.client.chat_client import create_and_run_client
from agentic_kernel.adk_chat.server.chat_server import create_and_run_server
from agentic_kernel.adk_chat.ui.mesop_ui import run_mesop_ui
from agentic_kernel.adk_chat.utils.adk_a2a_utils import setup_adk_a2a_environment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_server(host: str = "localhost", port: int = 8080) -> None:
    """Run the chat server.

    Args:
        host: The host for the server
        port: The port for the server
    """
    logger.info(f"Starting server on {host}:{port}")
    await create_and_run_server(host=host, port=port)


async def run_client(server_url: str = "http://localhost:8080") -> None:
    """Run the chat client.

    Args:
        server_url: The URL of the chat server
    """
    logger.info(f"Starting client connecting to {server_url}")
    await create_and_run_client(server_url=server_url)


async def run_both(
    server_host: str = "localhost",
    server_port: int = 8080,
) -> None:
    """Run both the server and client.

    Args:
        server_host: The host for the server
        server_port: The port for the server
    """
    # Start the server in a separate task
    server_task = asyncio.create_task(
        run_server(host=server_host, port=server_port),
    )

    # Wait a moment for the server to start
    await asyncio.sleep(2)

    # Start the client
    client_url = f"http://{server_host}:{server_port}"
    await run_client(server_url=client_url)

    # Cancel the server task when the client exits
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        logger.info("Server task cancelled")


def main() -> None:
    """Main entry point."""
    # Set up environment
    setup_adk_a2a_environment()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ADK A2A Chat System")
    parser.add_argument(
        "--mode",
        choices=["server", "client", "both", "mesop"],
        default="both",
        help="Run mode (server, client, both, or mesop UI)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port (default: 8080)",
    )
    parser.add_argument(
        "--server-url",
        default=None,
        help="Server URL for client mode (default: http://localhost:8080)",
    )

    args = parser.parse_args()

    # Run in the specified mode
    if args.mode == "server":
        asyncio.run(run_server(host=args.host, port=args.port))
    elif args.mode == "client":
        server_url = args.server_url or f"http://{args.host}:{args.port}"
        asyncio.run(run_client(server_url=server_url))
    elif args.mode == "mesop":
        # Start the server in a separate process
        import multiprocessing

        server_process = multiprocessing.Process(
            target=lambda: asyncio.run(run_server(host=args.host, port=args.port)),
        )
        server_process.start()

        # Wait a moment for the server to start
        import time

        time.sleep(2)

        try:
            # Run the Mesop UI
            run_mesop_ui()
        finally:
            # Terminate the server process when the UI exits
            server_process.terminate()
            server_process.join()
    else:  # both
        asyncio.run(run_both(server_host=args.host, server_port=args.port))


if __name__ == "__main__":
    main()
