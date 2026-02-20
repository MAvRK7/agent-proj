from orchestrator import orchestrator

conversation_history = []

if __name__ == "__main__":
    print("Welcome!")
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("\nEnter your query: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        
        response = orchestrator(user_input, conversation_history)
        print("\nAssistant:", response)