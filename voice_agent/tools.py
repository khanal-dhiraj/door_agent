"""
Tool definitions for Door Security Agent
These tools are available to the AI agent
"""

def get_tools():
    """Return the list of tools available to the agent"""
    return [
        {
            "type": "function",
            "name": "check_password",
            "description": "Validates if the provided password is correct",
            "parameters": {
                "type": "object",
                "properties": {
                    "password": {
                        "type": "string",
                        "description": "The password to validate"
                    }
                },
                "required": ["password"]
            }
        },
        {
            "type": "function",
            "name": "open_door",
            "description": "Opens the door after successful password validation",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]

# Additional tools can be added here:

# def get_extended_tools():
#     """Return extended tool set with additional capabilities"""
#     base_tools = get_tools()
#     additional_tools = [
#         {
#             "type": "function",
#             "name": "get_hint",
#             "description": "Provides a hint about the password",
#             "parameters": {
#                 "type": "object",
#                 "properties": {}
#             }
#         },
#         {
#             "type": "function",
#             "name": "reset_attempts",
#             "description": "Resets the attempt counter",
#             "parameters": {
#                 "type": "object",
#                 "properties": {}
#             }
#         }
#     ]
#     return base_tools + additional_tools