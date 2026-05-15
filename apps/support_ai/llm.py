class SimpleLLM:

    @staticmethod
    def generate_response(prompt, user_message):

        if "loan" in user_message.lower():
            return "You can apply for a loan from Loans section."

        if "fraud" in user_message.lower():
            return "We detected suspicious activity guidelines will be shown."

        return "I am your banking assistant. How can I help you?"
