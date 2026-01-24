"""
AST Path Listener for FHIRPath Parser

Forked from fhirpath-py and customized for FHIR4DS integration.
Original source: https://github.com/beda-software/fhirpath-py/tree/master/fhirpathpy/parser
"""

from antlr4.tree.Tree import TerminalNodeImpl
from .generated.FHIRPathListener import FHIRPathListener


def has_node_type_text(node_type):
    """
    Determine which node types should have text captured.

    In general we need mostly terminal nodes (e.g. Identifier and any Literal)
    But the code also uses TypeSpecifier, InvocationExpression and TermExpression
    """
    return node_type.endswith("Literal") or node_type in [
        "LiteralTerm",
        "Identifier",
        "TypeSpecifier",
        "InvocationExpression",
        "TermExpression",
    ]


# SP-024-001: Operator tokens for arithmetic, comparison, and logical expressions
OPERATOR_TOKENS = {
    # Arithmetic operators
    "+", "-", "*", "/", "div", "mod",
    # Comparison operators
    "=", "!=", "<>", "<", ">", "<=", ">=", "~", "!~",
    # Logical operators
    "and", "or", "xor", "implies",
    # Collection operators
    "|", "in", "contains",
    # Type operators
    "is", "as",
    # String operator
    "&",
}


def extract_operator_from_terminals(terminal_texts):
    """
    Extract the operator token from terminal node texts.
    
    SP-024-001: For operator expression nodes (AdditiveExpression, 
    MultiplicativeExpression, etc.), extract the actual operator
    from the terminal node texts.
    
    Args:
        terminal_texts: List of terminal node text strings
        
    Returns:
        The operator token if found, None otherwise
    """
    for text in terminal_texts:
        if text.lower() in OPERATOR_TOKENS or text in OPERATOR_TOKENS:
            return text
    return None


class ASTPathListener(FHIRPathListener):
    """
    Custom listener for building AST from FHIRPath parse tree.

    This listener captures the structure and content of parsed FHIRPath
    expressions to build an abstract syntax tree representation.
    """

    def __init__(self):
        """Initialize the listener with an empty parent stack"""
        self.parentStack = [{}]

    # SP-024-001: Node types that contain operator tokens
    OPERATOR_EXPRESSION_TYPES = {
        "AdditiveExpression",
        "MultiplicativeExpression",
        "PolarityExpression",
        "InequalityExpression",
        "EqualityExpression",
        "AndExpression",
        "OrExpression",
        "XorExpression",
        "ImpliesExpression",
        "UnionExpression",
        "MembershipExpression",
        "TypeExpression",
    }

    def pushNode(self, nodeType, ctx):
        """
        Create and push a new node onto the parent stack

        Args:
            nodeType: The type of the node being created
            ctx: The parse context containing node information
        """
        parentNode = self.parentStack[-1]
        node = {"type": nodeType, "terminalNodeText": []}

        # Capture text for nodes that should have it
        if has_node_type_text(nodeType):
            node["text"] = ctx.getText()

        # Capture terminal node text
        for child in ctx.children:
            if isinstance(child, TerminalNodeImpl):
                node["terminalNodeText"].append(child.getText())

        # SP-024-001: For operator expression nodes, extract operator token as text
        # This enables proper operator identification in the visitor pattern
        if nodeType in self.OPERATOR_EXPRESSION_TYPES:
            operator = extract_operator_from_terminals(node["terminalNodeText"])
            if operator:
                node["text"] = operator

        # Add node to parent's children
        if "children" not in parentNode:
            parentNode["children"] = []

        parentNode["children"].append(node)

        # Push this node as the new parent
        self.parentStack.append(node)

    def popNode(self):
        """Remove the current node from the parent stack"""
        if len(self.parentStack) > 0:
            self.parentStack.pop()

    def __getattribute__(self, name):
        """
        Dynamic method interception for listener callbacks

        This method automatically handles node creation and destruction
        by intercepting enter* and exit* method calls from the ANTLR listener.
        """
        attr = object.__getattribute__(self, name)

        if name in FHIRPathListener.__dict__ and callable(attr):

            def newfunc(*args, **kwargs):
                # Handle enter methods - create new node
                if name.startswith("enter"):
                    self.pushNode(name[5:], args[0])

                # Handle exit methods - pop current node
                if name.startswith("exit"):
                    self.popNode()

                return attr(*args, **kwargs)

            return newfunc
        return attr