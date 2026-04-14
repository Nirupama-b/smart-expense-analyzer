"""
Agent query service — placeholder for a future LangChain-powered SQL agent.
"""

import logging

logger = logging.getLogger(__name__)


class AgentQueryService:
    """
    Natural-language query interface for expense data.

    Currently returns a placeholder response; the full implementation will
    use a LangChain SQL agent connected to Supabase/Postgres.
    """

    @staticmethod
    def query(prompt: str, user_id: str) -> dict:
        """
        Process a natural-language question about the user's expenses.

        Parameters:
            prompt:  The user's question (e.g. "How much did I spend on
                     groceries last month?").
            user_id: The authenticated user's ID.

        Returns:
            A dict with ``status`` and ``response`` keys.
        """
        logger.info("Agent query from user %s: %s", user_id, prompt)

        return {
            "status": "coming_soon",
            "response": (
                "The natural-language query agent is coming soon. "
                "This feature will allow you to ask questions about your "
                "expenses in plain English."
            ),
        }

    # ------------------------------------------------------------------
    # Future implementation scaffolding (LangChain SQL agent)
    # ------------------------------------------------------------------
    # from langchain_community.utilities import SQLDatabase
    # from langchain_community.agent_toolkits import create_sql_agent
    # from langchain.agents import AgentType
    # from langchain_openai import ChatOpenAI
    #
    # @classmethod
    # def _build_agent(cls):
    #     """
    #     Build and cache a LangChain SQL agent connected to Supabase.
    #
    #     db = SQLDatabase.from_uri(os.getenv("DATABASE_URL"))
    #     llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    #     agent = create_sql_agent(
    #         llm=llm,
    #         db=db,
    #         agent_type=AgentType.OPENAI_FUNCTIONS,
    #         verbose=True,
    #     )
    #     return agent
    #     """
    #     pass
    #
    # @classmethod
    # def query_with_agent(cls, prompt: str, user_id: str) -> dict:
    #     """
    #     Run *prompt* through the SQL agent, scoped to *user_id*.
    #
    #     scoped_prompt = (
    #         f"Answer for user_id = '{user_id}' only. "
    #         f"Question: {prompt}"
    #     )
    #     agent = cls._build_agent()
    #     result = agent.invoke({"input": scoped_prompt})
    #     return {
    #         "status": "success",
    #         "response": result["output"],
    #     }
    #     """
    #     pass
