import os

def get_openai_api_key():
    """
    Retrieves the OpenAI API key from the environment variables.

    Returns:
        str: The OpenAI API key.

    Raises:
        EnvironmentError: If the API key is not found in the environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
    return api_key