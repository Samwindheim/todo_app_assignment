import pytest
import pytest_asyncio
from unittest import mock # For mocking the OpenAI API call
from openai import OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

# Important: Adjust the import path based on how you run pytest
# If running pytest from the *project root*:
from backend.main import get_labels_for_task

# If running pytest from the *backend* directory:
# from main import get_labels_for_task, aclient

# --- Test Fixtures (if needed later) ---

# --- Test Cases for get_labels_for_task ---

@pytest.mark.asyncio
async def test_get_labels_success():
    """Test successful label generation from OpenAI response."""
    # Arrange: Create the mock completion object
    mock_completion = ChatCompletion(
        id="chatcmpl-xxxxx",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(content="work, urgent", role="assistant", function_call=None, tool_calls=None)
            )
        ],
        created=1677652288, model="gpt-3.5-turbo-0613", object="chat.completion", system_fingerprint="fp_xxxxx", usage=None
    )

    # Patch the create method using AsyncMock for awaitable behavior
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, return_value=mock_completion) as mock_create:
        # Act: Call the function under test
        labels = await get_labels_for_task("Fix critical bug", "Login fails for users")

        # Assert: Check the results
        assert labels == "work, urgent"
        mock_create.assert_called_once() # Corrected assertion

@pytest.mark.asyncio
async def test_get_labels_returns_none():
    """Test when OpenAI responds with 'None' or similar."""
    # Arrange
    mock_completion = ChatCompletion(
        id="chatcmpl-xxxxx",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(content=" None ", role="assistant", function_call=None, tool_calls=None)
            )
        ],
        created=1677652288, model="gpt-3.5-turbo-0613", object="chat.completion", system_fingerprint="fp_xxxxx", usage=None
    )
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, return_value=mock_completion) as mock_create:
        # Act
        labels = await get_labels_for_task("Simple task", "Nothing special")
        # Assert
        assert labels is None
        mock_create.assert_called_once() # Corrected assertion

@pytest.mark.asyncio
async def test_get_labels_openai_error():
    """Test fallback when OpenAI API raises an error."""
    # Arrange: Mock the API call to raise an OpenAIError
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, side_effect=OpenAIError("API connection error")) as mock_create:
        # Act
        labels = await get_labels_for_task("Another task", "")
        # Assert
        assert labels is None # Should return None as fallback
        mock_create.assert_called_once() # Corrected assertion

@pytest.mark.asyncio
async def test_get_labels_no_client():
    """Test behavior when OpenAI client (aclient) is None (e.g., no API key)."""
    # Arrange: Patch the 'aclient' directly where get_labels_for_task uses it
    with mock.patch('backend.main.aclient', None):
        # Act
        labels = await get_labels_for_task("Task without client", "")
        # Assert
        assert labels is None

# Note: Removed redundant import of aclient as we mock it where needed
# Note: Removed TODO as these core cases cover the main logic paths 