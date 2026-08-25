import asyncio
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_server():
    logger.info("Starting Golden Demo MCP Server")
    
    # Send init response if we were actually implementing the full protocol handshake, 
    # but since this is for testing, we just need to respond to tool requests.
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            try:
                request = json.loads(line)
                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})
                
                if method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "get_job_description",
                                    "description": "Retrieves the stored job description for a role.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "role": {"type": "string"}
                                        },
                                        "required": ["role"]
                                    }
                                },
                                {
                                    "name": "hire_candidate",
                                    "description": "Formally hires the candidate. HIGH RISK ACTION.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "salary_usd": {"type": "integer"}
                                        },
                                        "required": ["name", "salary_usd"]
                                    }
                                }
                            ]
                        }
                    }
                elif method == "tools/call":
                    tool_name = params.get("name")
                    args = params.get("arguments", {})
                    
                    if tool_name == "get_job_description":
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "content": [{"type": "text", "text": "Job Description: Senior Engineer, Salary: $150000"}]
                            }
                        }
                    elif tool_name == "hire_candidate":
                        salary = args.get("salary_usd")
                        if not isinstance(salary, int):
                            response = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": f"Invalid params: salary_usd must be an integer, got {type(salary).__name__}"
                                }
                            }
                        else:
                            response = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "content": [{"type": "text", "text": f"Successfully hired {args.get('name')} at ${salary}"}]
                                }
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32601, "message": "Method not found"}
                        }
                else:
                    # Ignore other methods
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {}
                    }
                    
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            break

if __name__ == "__main__":
    asyncio.run(run_server())
