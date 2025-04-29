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
# These tests verify the logic within the `get_labels_for_task` function
# by simulating different responses or errors from the OpenAI API call.

@pytest.mark.asyncio # Mark the test as asynchronous to work with async functions
async def test_get_labels_success():
    """Test successful label generation from OpenAI response."""
    # ARRANGE: Set up the test conditions and mock data.
    # -----------------------------------------------------
    # 1. Define the *expected* fake response object from OpenAI.
    #    We mimic the structure the real API would return.
    mock_completion = ChatCompletion(
        id="chatcmpl-mock-success",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                # Simulate the AI returning the desired labels
                message=ChatCompletionMessage(content="work, urgent", role="assistant", function_call=None, tool_calls=None)
            )
        ],
        created=1677652288, model="gpt-3.5-turbo", object="chat.completion"
    )

    # 2. Patch the actual function that makes the API call.
    #    - We target 'backend.main.aclient.chat.completions.create' which is called inside get_labels_for_task.
    #    - `new_callable=mock.AsyncMock` ensures the mock behaves like an async function that can be awaited.
    #    - `return_value=mock_completion` tells the mock to return our predefined fake response when called.
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, return_value=mock_completion) as mock_create:

        # ACT: Execute the code being tested.
        # ----------------------------------
        labels = await get_labels_for_task("Fix critical bug", "Login fails for users")

        # ASSERT: Verify the outcome.
        # ---------------------------
        # 1. Check if the function processed the mock response correctly.
        assert labels == "work, urgent"
        # 2. Verify that the mocked API call function was actually called exactly once.
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_get_labels_returns_none():
    """Test when OpenAI responds with 'None', indicating no relevant labels."""
    # ARRANGE: Mock an API response containing " None ".
    # -----------------------------------------------------
    mock_completion = ChatCompletion(
        id="chatcmpl-mock-none",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                # Simulate the AI explicitly returning " None "
                message=ChatCompletionMessage(content=" None ", role="assistant", function_call=None, tool_calls=None)
            )
        ],
        created=1677652288, model="gpt-3.5-turbo", object="chat.completion"
    )
    # Patch the API call to return this specific response.
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, return_value=mock_completion) as mock_create:
        # ACT: Run the function.
        # -------------------
        labels = await get_labels_for_task("Simple task", "Nothing special")
        # ASSERT: Check if the function correctly interpreted " None " as Python None.
        # -----------------------------------------------------------------------
        assert labels is None
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_get_labels_openai_error():
    """Test the fallback behavior when the OpenAI API call raises an error. Rate limits, etc."""
    # ARRANGE: Configure the mock to raise an OpenAIError when called.
    #          `side_effect` makes the mock raise an exception instead of returning a value.
    # ------------------------------------------------------------------------------------
    with mock.patch('backend.main.aclient.chat.completions.create', new_callable=mock.AsyncMock, side_effect=OpenAIError("Mock API connection error")) as mock_create:
        # ACT: Run the function.
        # -------------------
        labels = await get_labels_for_task("Another task", "")
        # ASSERT: Check if the function returned None as the fallback on error.
        # ----------------------------------------------------------------------
        assert labels is None
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_get_labels_no_client():
    """Test behavior when the OpenAI client itself is None (e.g., no API key)."""
    # ARRANGE: Patch the *aclient variable* directly within the backend.main module,
    #          setting it to None for the duration of this test.
    #          This simulates the state where the API key wasn't loaded.
    # ----------------------------------------------------------------------------
    with mock.patch('backend.main.aclient', None):
        # ACT: Run the function.
        # -------------------
        labels = await get_labels_for_task("Task without client", "")
        # ASSERT: Check if the function returned None immediately due to the `if not aclient:` check.
        #          Note: We don't assert the API call count here because it should *not* have been called.
        # ------------------------------------------------------------------------------------------------
        assert labels is None
