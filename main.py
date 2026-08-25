#!/usr/bin/env python3
"""
AgentOS — Main Entry Point

Run the entire system with a single command:
    python main.py

This starts:
    1. Validates required env vars
    2. Creates data/ dir and SQLite DB if missing
    3. Generates RSA keypair on first run
    4. Runs npm install if node_modules missing
    5. Starts FastAPI backend on port 8000 (--reload)
    6. Starts Next.js frontend on port 3000
    7. Health-checks both services
    8. Prints clear status summary
    9. Multiplexes logs with [BACKEND] / [FRONTEND] prefixes
    10. Shuts everything down cleanly on Ctrl+C
"""

import os
import sys
import signal
import subprocess
import time
import threading
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Configuration ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"
KEYS_DIR = PROJECT_ROOT / "backend" / "security" / "keys"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# Load .env first
load_dotenv(PROJECT_ROOT / ".env")

BACKEND_HOST = os.environ.get("API_HOST", "127.0.0.1")
BACKEND_PORT = os.environ.get("API_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "3000")


# ── Logging with prefixed output ──────────────────────────────────

class PrefixedLogger:
    """Multiplexes subprocess output with [PREFIX] tags."""

    def __init__(self, prefix: str, stream=sys.stdout):
        self.prefix = prefix
        self.stream = stream

    def pipe_output(self, pipe, is_error=False):
        """Read from a pipe line-by-line and write with prefix."""
        try:
            for line in iter(pipe.readline, b''):
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded:
                    self.stream.write(f"  {self.prefix} {decoded}\n")
                    self.stream.flush()
        except (ValueError, OSError):
            pass  # Pipe closed


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("agentos")


# ── Pre-flight Checks ────────────────────────────────────────────

def validate_environment(logger) -> bool:
    """Validate required environment variables and dependencies."""
    errors = []

    # Check GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or len(api_key) < 10:
        errors.append(
            "GEMINI_API_KEY is missing or invalid.\n"
            "   Get one free at: https://aistudio.google.com/apikey\n"
            "   Then add to .env: GEMINI_API_KEY=your_key_here"
        )

    # Check Python
    python_path = find_python()
    if not python_path:
        errors.append("Python not found. Expected .venv/bin/python")

    # Check required Python packages
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import fastapi, aiosqlite, bcrypt, jwt, cryptography"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            errors.append(
                "Missing Python dependencies. Run:\n"
                "   pip install -r requirements.txt"
            )
    except Exception:
        pass

    if errors:
        logger.error("=" * 60)
        logger.error("  PRE-FLIGHT CHECK FAILED")
        logger.error("=" * 60)
        for i, err in enumerate(errors, 1):
            logger.error(f"\n  {i}. {err}")
        logger.error("")
        return False

    return True


def ensure_directories(logger):
    """Create required directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directory: {DATA_DIR}")


def ensure_rsa_keys(logger):
    """Generate RSA keypair on first run if missing."""
    private_key_path = KEYS_DIR / "private.pem"
    public_key_path = KEYS_DIR / "public.pem"

    if private_key_path.exists() and public_key_path.exists():
        logger.info("RSA keypair: exists")
        return

    logger.info("Generating RSA-2048 keypair for JWT signing...")
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Write private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_path.write_bytes(private_pem)
    os.chmod(str(private_key_path), 0o600)

    # Write public key
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key_path.write_bytes(public_pem)

    logger.info("RSA keypair generated and saved to backend/security/keys/")


def ensure_frontend_deps(logger) -> bool:
    """Run npm install if node_modules is missing."""
    node_modules = FRONTEND_DIR / "node_modules"
    npm_path = find_npm()

    if not npm_path:
        logger.warning("npm not found — frontend will not start")
        return False

    if not node_modules.exists():
        logger.info("Installing frontend dependencies (npm install)...")
        result = subprocess.run(
            [npm_path, "install"],
            cwd=str(FRONTEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logger.error(f"npm install failed:\n{result.stderr[:500]}")
            return False
        logger.info("Frontend dependencies installed")

    return True


# ── Process Management ────────────────────────────────────────────

def find_python() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def find_npm() -> str:
    import shutil
    return shutil.which("npm")


def start_backend(python_path: str, logger_obj) -> subprocess.Popen:
    """Start the FastAPI backend via uvicorn."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    proc = subprocess.Popen(
        [
            python_path, "-m", "uvicorn",
            "backend.api.main:app",
            "--host", BACKEND_HOST,
            "--port", BACKEND_PORT,
            "--reload",
            "--reload-dir", str(PROJECT_ROOT / "backend"),
            "--log-level", "info",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Start output threads with prefix
    prefix_logger = PrefixedLogger("\033[36m[BACKEND]\033[0m")
    threading.Thread(
        target=prefix_logger.pipe_output, args=(proc.stdout,), daemon=True
    ).start()
    threading.Thread(
        target=prefix_logger.pipe_output, args=(proc.stderr, True), daemon=True
    ).start()

    return proc


def start_frontend(npm_path: str) -> subprocess.Popen:
    """Start the Next.js frontend dev server."""
    env = os.environ.copy()
    env["PORT"] = FRONTEND_PORT

    proc = subprocess.Popen(
        [npm_path, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    prefix_logger = PrefixedLogger("\033[35m[FRONTEND]\033[0m")
    threading.Thread(
        target=prefix_logger.pipe_output, args=(proc.stdout,), daemon=True
    ).start()
    threading.Thread(
        target=prefix_logger.pipe_output, args=(proc.stderr, True), daemon=True
    ).start()

    return proc


def health_check(url: str, retries: int = 10, delay: float = 2.0) -> bool:
    """Check if a service is healthy."""
    import urllib.request
    for attempt in range(retries):
        try:
            req = urllib.request.urlopen(url, timeout=3)
            if req.status == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def print_banner(logger, has_frontend: bool):
    """Print the startup banner."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ╔═══════════════════════════════════════════╗")
    logger.info("  ║           AgentOS v2.0.0                  ║")
    logger.info("  ║   The autonomous workspace that           ║")
    logger.info("  ║   builds its own tools.                   ║")
    logger.info("  ╚═══════════════════════════════════════════╝")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"  Backend:   http://{BACKEND_HOST}:{BACKEND_PORT}")
    logger.info(f"  API Docs:  http://{BACKEND_HOST}:{BACKEND_PORT}/api/docs")
    if has_frontend:
        logger.info(f"  Frontend:  http://localhost:{FRONTEND_PORT}")
    logger.info(f"  Storage:   {os.environ.get('STORAGE_BACKEND', 'sqlite')}")
    logger.info(f"  Model:     {os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')}")
    logger.info("")
    logger.info("  Press Ctrl+C to stop all services")
    logger.info("=" * 60)
    logger.info("")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    logger = setup_logging()

    # 1. Pre-flight checks
    if not validate_environment(logger):
        sys.exit(1)

    # 2. Ensure directories
    ensure_directories(logger)

    # 3. Generate RSA keys if needed
    ensure_rsa_keys(logger)

    # 4. Check frontend deps
    npm_path = find_npm()
    has_frontend = False
    if npm_path:
        has_frontend = ensure_frontend_deps(logger)

    # 5. Start services
    python_path = find_python()
    processes = []

    try:
        logger.info("Starting backend...")
        backend_proc = start_backend(python_path, logger)
        processes.append(("Backend", backend_proc))

        # Wait for backend to start
        logger.info("Waiting for backend health check...")
        backend_healthy = health_check(f"http://{BACKEND_HOST}:{BACKEND_PORT}/health")
        if backend_healthy:
            logger.info("Backend: \033[32mHEALTHY\033[0m")
        else:
            logger.warning("Backend: health check timed out (may still be starting)")

        if has_frontend and npm_path:
            logger.info("Starting frontend...")
            frontend_proc = start_frontend(npm_path)
            processes.append(("Frontend", frontend_proc))

            # Wait for frontend
            logger.info("Waiting for frontend health check...")
            frontend_healthy = health_check(f"http://localhost:{FRONTEND_PORT}", retries=15)
            if frontend_healthy:
                logger.info("Frontend: \033[32mHEALTHY\033[0m")
            else:
                logger.warning("Frontend: health check timed out (may still be starting)")
        else:
            logger.warning("Frontend not started (npm not available)")

        # 6. Print status banner
        print_banner(logger, has_frontend)

        # 7. Wait for processes, monitor for crashes
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    logger.error(f"{name} exited unexpectedly with code {ret}")
                    raise SystemExit(ret)
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n\033[33mShutting down gracefully...\033[0m")
    except SystemExit:
        pass
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                logger.info(f"  Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        logger.info("All services stopped. Goodbye!")


if __name__ == "__main__":
    main()
