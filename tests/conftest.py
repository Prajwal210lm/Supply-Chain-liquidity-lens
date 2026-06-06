"""Load .env at collection time so environment-dependent skipif decorators
(e.g. @pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))) see the
values before they are evaluated. pytest imports conftest.py before collecting
the tests in this directory, which is earlier than any test-body load_dotenv().
"""

from dotenv import load_dotenv

load_dotenv()
