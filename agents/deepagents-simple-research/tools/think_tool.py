"""Think tool for agent reflection during research.

This tool provides a structured way for agents to pause and reflect on their
research progress, following the pattern from Anthropic's "Claude Think Tool":
https://www.anthropic.com/engineering/claude-think-tool

The think tool helps audit agent decision-making by making reasoning explicit.
"""

from langchain_core.tools import tool

from shared.emitter import emit_think


@tool
def think_tool(thought: str) -> str:
    """Use this tool to pause and reflect on your research progress.
    
    CRITICAL: Use this tool after EVERY search to analyze results and plan next steps.
    
    This is a thinking/reflection tool - it does not perform any external actions.
    Use it to:
    - Analyze what key information you found
    - Identify what's still missing
    - Decide if you have enough to answer comprehensively
    - Plan your next search query (if needed)
    
    Args:
        thought: Your reflection on the current research state. Should include:
            - Summary of key findings so far
            - Gaps in information
            - Assessment of whether you can answer the question
            - Next steps (search more or provide answer)
    
    Returns:
        Acknowledgment that the thought was recorded
    
    Example:
        think_tool(thought='''
        Key findings so far:
        - Found 3 sources about context engineering techniques
        - RAG and memory management are the main approaches
        
        Gaps:
        - Need more information about specific frameworks (LangChain, LlamaIndex)
        
        Assessment:
        - Have good overview but missing implementation details
        
        Next step:
        - Search for "LangChain LlamaIndex context management comparison"
        ''')
    """
    # Emit think event for frontend visibility
    emit_think(thought)
    
    # The tool simply acknowledges the thought - the value is in making
    # the reasoning explicit and auditable in the trace
    return "Thought recorded. Continue with your research based on this reflection."
